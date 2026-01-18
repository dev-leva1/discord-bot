import discord
from discord import app_commands
import json
from pathlib import Path


class RoleRewards:
    def __init__(self, bot):
        self.bot = bot
        self.config_file = Path("data") / "role_rewards.json"
        self.config = self.load_config()

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                return json.load(f)
        return {}

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    async def setup(self):
        @self.bot.tree.command(
            name="addrole", description="Добавить роль-награду за достижение определенного уровня"
        )
        @app_commands.checks.has_permissions(manage_roles=True)
        async def addrole(interaction: discord.Interaction, role: discord.Role, level: int):
            guild_id = str(interaction.guild.id)

            if guild_id not in self.config:
                self.config[guild_id] = {}

            self.config[guild_id][str(level)] = role.id
            self.save_config()

            embed = discord.Embed(
                title="Роль-награда добавлена",
                description=f"Роль {role.mention} будет выдаваться при достижении {level} уровня",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(name="removerole", description="Удалить роль-награду за уровень")
        @app_commands.checks.has_permissions(manage_roles=True)
        async def removerole(interaction: discord.Interaction, level: int):
            guild_id = str(interaction.guild.id)

            if guild_id not in self.config or str(level) not in self.config[guild_id]:
                await interaction.response.send_message(
                    "Для этого уровня не настроена роль-награда!", ephemeral=True
                )
                return

            role_id = self.config[guild_id].pop(str(level))
            self.save_config()

            role = interaction.guild.get_role(role_id)
            role_name = role.mention if role else "Удаленная роль"

            embed = discord.Embed(
                title="Роль-награда удалена",
                description=f"Роль {role_name} больше не будет выдаваться за {level} уровень",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(
            name="listroles", description="Показать список ролей-наград за уровни"
        )
        async def listroles(interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)

            if guild_id not in self.config or not self.config[guild_id]:
                await interaction.response.send_message(
                    "На сервере нет настроенных ролей-наград!", ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Роли за уровни",
                description="Список ролей, которые выдаются за достижение уровней:",
                color=discord.Color.blue(),
            )

            for level, role_id in sorted(self.config[guild_id].items(), key=lambda x: int(x[0])):
                role = interaction.guild.get_role(role_id)
                if role:
                    embed.add_field(name=f"Уровень {level}", value=role.mention, inline=False)

            await interaction.response.send_message(embed=embed)

    async def check_level_up(self, member: discord.Member, new_level: int):
        guild_id = str(member.guild.id)

        if guild_id not in self.config:
            return

        for level, role_id in self.config[guild_id].items():
            level = int(level)
            if new_level >= level:
                role = member.guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except discord.Forbidden:
                        pass  # Нет прав для выдачи роли
