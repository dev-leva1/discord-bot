"""Тесты для системы ролей-наград за уровни."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from pathlib import Path
import json

from roles import RoleRewards


class TestRoleRewardsConfiguration:
    """Тесты конфигурации системы ролей-наград."""

    @pytest.fixture
    def role_rewards(self, tmp_path):
        """Фикстура для создания системы ролей-наград."""
        bot = MagicMock()
        system = RoleRewards(bot)
        system.config_file = tmp_path / "role_rewards.json"
        return system

    def test_load_config_creates_empty_if_not_exists(self, role_rewards):
        """Тест создания пустой конфигурации если файл не существует."""
        config = role_rewards.load_config()
        assert config == {}

    def test_load_config_reads_existing_file(self, role_rewards):
        """Тест чтения существующего файла конфигурации."""
        test_config = {"123456": {"5": 789012, "10": 111111}}
        role_rewards.config_file.write_text(json.dumps(test_config))

        config = role_rewards.load_config()

        assert config == test_config

    def test_save_config_writes_to_file(self, role_rewards):
        """Тест сохранения конфигурации в файл."""
        role_rewards.config = {"123456": {"5": 789012}}

        role_rewards.save_config()

        saved_data = json.loads(role_rewards.config_file.read_text())
        assert saved_data == role_rewards.config


class TestRoleRewardsSetup:
    """Тесты настройки команд."""

    @pytest.fixture
    def role_rewards(self, tmp_path):
        """Фикстура для создания системы ролей-наград."""
        bot = MagicMock()
        bot.tree = MagicMock()
        system = RoleRewards(bot)
        system.config_file = tmp_path / "role_rewards.json"
        system.config = {}
        return system

    @pytest.mark.asyncio
    async def test_setup_registers_commands(self, role_rewards):
        """Тест регистрации команд."""
        await role_rewards.setup()

        # Должны быть зарегистрированы 3 команды
        assert role_rewards.bot.tree.command.call_count == 3


class TestRoleRewardsAddRole:
    """Тесты добавления ролей-наград."""

    @pytest.fixture
    def role_rewards(self, tmp_path):
        """Фикстура для создания системы ролей-наград."""
        bot = MagicMock()

        # Сохраняем зарегистрированные команды
        registered_commands = {}

        def mock_command(**kwargs):
            def decorator(func):
                registered_commands[kwargs.get('name', func.__name__)] = func
                return func
            return decorator

        bot.tree.command = mock_command

        system = RoleRewards(bot)
        system.config_file = tmp_path / "role_rewards.json"
        system.config = {}
        system._registered_commands = registered_commands
        return system

    @pytest.mark.asyncio
    async def test_addrole_command_success(self, role_rewards):
        """Тест успешного добавления роли-награды."""
        await role_rewards.setup()

        # Получаем зарегистрированную команду
        addrole_func = role_rewards._registered_commands['addrole']

        guild = MagicMock()
        guild.id = 123456

        role = MagicMock(spec=discord.Role)
        role.id = 789012
        role.mention = "@TestRole"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await addrole_func(interaction, role, 5)

        # Проверяем что роль добавлена в конфиг
        assert "123456" in role_rewards.config
        assert "5" in role_rewards.config["123456"]
        assert role_rewards.config["123456"]["5"] == 789012

        # Проверяем что отправлен embed
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_addrole_command_creates_guild_config(self, role_rewards):
        """Тест создания конфига для новой гильдии."""
        await role_rewards.setup()

        addrole_func = role_rewards._registered_commands['addrole']

        guild = MagicMock()
        guild.id = 999999  # Новая гильдия

        role = MagicMock(spec=discord.Role)
        role.id = 789012
        role.mention = "@TestRole"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await addrole_func(interaction, role, 10)

        # Проверяем что создан конфиг для гильдии
        assert "999999" in role_rewards.config
        assert "10" in role_rewards.config["999999"]

    @pytest.mark.asyncio
    async def test_addrole_command_overwrites_existing(self, role_rewards):
        """Тест перезаписи существующей роли для уровня."""
        role_rewards.config = {"123456": {"5": 111111}}

        await role_rewards.setup()

        addrole_func = role_rewards._registered_commands['addrole']

        guild = MagicMock()
        guild.id = 123456

        role = MagicMock(spec=discord.Role)
        role.id = 789012
        role.mention = "@NewRole"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await addrole_func(interaction, role, 5)

        # Проверяем что роль перезаписана
        assert role_rewards.config["123456"]["5"] == 789012


class TestRoleRewardsRemoveRole:
    """Тесты удаления ролей-наград."""

    @pytest.fixture
    def role_rewards(self, tmp_path):
        """Фикстура для создания системы ролей-наград."""
        bot = MagicMock()

        # Сохраняем зарегистрированные команды
        registered_commands = {}

        def mock_command(**kwargs):
            def decorator(func):
                registered_commands[kwargs.get('name', func.__name__)] = func
                return func
            return decorator

        bot.tree.command = mock_command

        system = RoleRewards(bot)
        system.config_file = tmp_path / "role_rewards.json"
        system.config = {"123456": {"5": 789012, "10": 111111}}
        system._registered_commands = registered_commands
        return system

    @pytest.mark.asyncio
    async def test_removerole_command_success(self, role_rewards):
        """Тест успешного удаления роли-награды."""
        await role_rewards.setup()

        # Получаем зарегистрированную команду
        removerole_func = role_rewards._registered_commands['removerole']

        guild = MagicMock()
        guild.id = 123456

        role = MagicMock(spec=discord.Role)
        role.mention = "@TestRole"
        guild.get_role = MagicMock(return_value=role)

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await removerole_func(interaction, 5)

        # Проверяем что роль удалена из конфига
        assert "5" not in role_rewards.config["123456"]
        assert "10" in role_rewards.config["123456"]  # Другая роль осталась

        # Проверяем что отправлен embed
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_removerole_command_no_role_for_level(self, role_rewards):
        """Тест удаления роли когда для уровня нет роли."""
        await role_rewards.setup()

        removerole_func = role_rewards._registered_commands['removerole']

        guild = MagicMock()
        guild.id = 123456

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await removerole_func(interaction, 99)  # Нет роли для уровня 99

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не настроена" in call_args.lower()

    @pytest.mark.asyncio
    async def test_removerole_command_no_guild_config(self, role_rewards):
        """Тест удаления роли когда нет конфига для гильдии."""
        role_rewards.config = {}

        await role_rewards.setup()

        removerole_func = role_rewards._registered_commands['removerole']

        guild = MagicMock()
        guild.id = 999999  # Нет в конфиге

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await removerole_func(interaction, 5)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не настроена" in call_args.lower()

    @pytest.mark.asyncio
    async def test_removerole_command_deleted_role(self, role_rewards):
        """Тест удаления когда роль уже удалена из Discord."""
        await role_rewards.setup()

        removerole_func = role_rewards._registered_commands['removerole']

        guild = MagicMock()
        guild.id = 123456
        guild.get_role = MagicMock(return_value=None)  # Роль не найдена

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await removerole_func(interaction, 5)

        # Проверяем что роль удалена из конфига
        assert "5" not in role_rewards.config["123456"]

        # Проверяем что отправлен embed с "Удаленная роль"
        interaction.response.send_message.assert_called_once()


class TestRoleRewardsListRoles:
    """Тесты списка ролей-наград."""

    @pytest.fixture
    def role_rewards(self, tmp_path):
        """Фикстура для создания системы ролей-наград."""
        bot = MagicMock()

        # Сохраняем зарегистрированные команды
        registered_commands = {}

        def mock_command(**kwargs):
            def decorator(func):
                registered_commands[kwargs.get('name', func.__name__)] = func
                return func
            return decorator

        bot.tree.command = mock_command

        system = RoleRewards(bot)
        system.config_file = tmp_path / "role_rewards.json"
        system.config = {"123456": {"5": 789012, "10": 111111, "15": 222222}}
        system._registered_commands = registered_commands
        return system

    @pytest.mark.asyncio
    async def test_listroles_command_success(self, role_rewards):
        """Тест успешного получения списка ролей."""
        await role_rewards.setup()

        # Получаем зарегистрированную команду
        listroles_func = role_rewards._registered_commands['listroles']

        guild = MagicMock()
        guild.id = 123456

        role1 = MagicMock(spec=discord.Role)
        role1.mention = "@Role5"

        role2 = MagicMock(spec=discord.Role)
        role2.mention = "@Role10"

        role3 = MagicMock(spec=discord.Role)
        role3.mention = "@Role15"

        def get_role(role_id):
            if role_id == 789012:
                return role1
            elif role_id == 111111:
                return role2
            elif role_id == 222222:
                return role3
            return None

        guild.get_role = get_role

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await listroles_func(interaction)

        # Проверяем что отправлен embed
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "embed" in call_args.kwargs

        embed = call_args.kwargs["embed"]
        # Проверяем что есть 3 поля (по одному на каждую роль)
        assert len(embed.fields) == 3

    @pytest.mark.asyncio
    async def test_listroles_command_no_roles(self, role_rewards):
        """Тест списка когда нет ролей."""
        role_rewards.config = {}

        await role_rewards.setup()

        listroles_func = role_rewards._registered_commands['listroles']

        guild = MagicMock()
        guild.id = 123456

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await listroles_func(interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "нет настроенных" in call_args.lower()

    @pytest.mark.asyncio
    async def test_listroles_command_empty_guild_config(self, role_rewards):
        """Тест списка когда конфиг гильдии пустой."""
        role_rewards.config = {"123456": {}}

        await role_rewards.setup()

        listroles_func = role_rewards._registered_commands['listroles']

        guild = MagicMock()
        guild.id = 123456

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await listroles_func(interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "нет настроенных" in call_args.lower()

    @pytest.mark.asyncio
    async def test_listroles_command_sorted_by_level(self, role_rewards):
        """Тест что роли отсортированы по уровню."""
        # Специально создаем неотсортированный конфиг
        role_rewards.config = {"123456": {"15": 222222, "5": 789012, "10": 111111}}

        await role_rewards.setup()

        listroles_func = role_rewards._registered_commands['listroles']

        guild = MagicMock()
        guild.id = 123456

        role1 = MagicMock(spec=discord.Role)
        role1.mention = "@Role5"

        role2 = MagicMock(spec=discord.Role)
        role2.mention = "@Role10"

        role3 = MagicMock(spec=discord.Role)
        role3.mention = "@Role15"

        def get_role(role_id):
            if role_id == 789012:
                return role1
            elif role_id == 111111:
                return role2
            elif role_id == 222222:
                return role3
            return None

        guild.get_role = get_role

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await listroles_func(interaction)

        embed = interaction.response.send_message.call_args.kwargs["embed"]

        # Проверяем что поля отсортированы по уровню
        assert "5" in embed.fields[0].name
        assert "10" in embed.fields[1].name
        assert "15" in embed.fields[2].name


class TestRoleRewardsCheckLevelUp:
    """Тесты автоматической выдачи ролей при повышении уровня."""

    @pytest.fixture
    def role_rewards(self, tmp_path):
        """Фикстура для создания системы ролей-наград."""
        bot = MagicMock()
        system = RoleRewards(bot)
        system.config_file = tmp_path / "role_rewards.json"
        system.config = {"123456": {"5": 789012, "10": 111111, "15": 222222}}
        return system

    @pytest.mark.asyncio
    async def test_check_level_up_adds_role(self, role_rewards):
        """Тест выдачи роли при достижении уровня."""
        guild = MagicMock()
        guild.id = 123456

        role = MagicMock(spec=discord.Role)
        guild.get_role = MagicMock(return_value=role)

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.roles = []
        member.add_roles = AsyncMock()

        await role_rewards.check_level_up(member, 5)

        # Проверяем что роль выдана
        member.add_roles.assert_called_once_with(role)

    @pytest.mark.asyncio
    async def test_check_level_up_multiple_roles(self, role_rewards):
        """Тест выдачи нескольких ролей при высоком уровне."""
        guild = MagicMock()
        guild.id = 123456

        role5 = MagicMock(spec=discord.Role)
        role10 = MagicMock(spec=discord.Role)

        def get_role(role_id):
            if role_id == 789012:
                return role5
            elif role_id == 111111:
                return role10
            return None

        guild.get_role = get_role

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.roles = []
        member.add_roles = AsyncMock()

        await role_rewards.check_level_up(member, 10)

        # Проверяем что выданы обе роли (5 и 10 уровня)
        assert member.add_roles.call_count == 2

    @pytest.mark.asyncio
    async def test_check_level_up_already_has_role(self, role_rewards):
        """Тест что роль не выдается если уже есть."""
        guild = MagicMock()
        guild.id = 123456

        role = MagicMock(spec=discord.Role)
        guild.get_role = MagicMock(return_value=role)

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.roles = [role]  # Роль уже есть
        member.add_roles = AsyncMock()

        await role_rewards.check_level_up(member, 5)

        # Проверяем что роль не выдана повторно
        member.add_roles.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_level_up_no_guild_config(self, role_rewards):
        """Тест когда нет конфига для гильдии."""
        guild = MagicMock()
        guild.id = 999999  # Нет в конфиге

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.add_roles = AsyncMock()

        # Не должно быть ошибки
        await role_rewards.check_level_up(member, 5)

        member.add_roles.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_level_up_handles_forbidden(self, role_rewards):
        """Тест обработки ошибки прав при выдаче роли."""
        guild = MagicMock()
        guild.id = 123456

        role = MagicMock(spec=discord.Role)
        guild.get_role = MagicMock(return_value=role)

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.roles = []
        member.add_roles = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "No permission"))

        # Не должно быть исключения
        await role_rewards.check_level_up(member, 5)

    @pytest.mark.asyncio
    async def test_check_level_up_role_not_found(self, role_rewards):
        """Тест когда роль не найдена в Discord."""
        guild = MagicMock()
        guild.id = 123456
        guild.get_role = MagicMock(return_value=None)  # Роль не найдена

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.roles = []
        member.add_roles = AsyncMock()

        # Не должно быть ошибки
        await role_rewards.check_level_up(member, 5)

        member.add_roles.assert_not_called()
