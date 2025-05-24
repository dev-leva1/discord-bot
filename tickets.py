import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
from datetime import datetime

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets_config = self.load_config()

    async def setup(self):
        """Инициализация системы тикетов"""
        print("Система тикетов готова к работе")

    def load_config(self):
        try:
            with open('tickets_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "ticket_category": None,
                "support_role": None,
                "ticket_counter": 0
            }
            with open('tickets_config.json', 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def save_config(self):
        with open('tickets_config.json', 'w') as f:
            json.dump(self.tickets_config, f, indent=4)

    @app_commands.command(name="ticket_setup", description="Настроить систему тикетов")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        category="Категория для тикетов",
        support_role="Роль поддержки"
    )
    async def setup_tickets(self, interaction: discord.Interaction, category: discord.CategoryChannel, support_role: discord.Role):
        self.tickets_config["ticket_category"] = category.id
        self.tickets_config["support_role"] = support_role.id
        self.save_config()
        await interaction.response.send_message(
            f"Система тикетов настроена!\nКатегория: {category.name}\nРоль поддержки: {support_role.name}"
        )

    @app_commands.command(name="ticket_create", description="Создать тикет")
    @app_commands.describe(reason="Причина создания тикета")
    async def create_ticket(self, interaction: discord.Interaction, reason: str = "Не указана"):
        if not self.tickets_config["ticket_category"]:
            return await interaction.response.send_message(
                "Система тикетов не настроена! Администратор должен выполнить команду /ticket_setup",
                ephemeral=True
            )

        self.tickets_config["ticket_counter"] += 1
        ticket_number = self.tickets_config["ticket_counter"]
        
        category = self.bot.get_channel(self.tickets_config["ticket_category"])
        support_role = interaction.guild.get_role(self.tickets_config["support_role"])

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await category.create_text_channel(
            f"ticket-{ticket_number}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"Тикет #{ticket_number}",
            description=f"**Причина:** {reason}\n**Создатель:** {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        await channel.send(f"{support_role.mention}", embed=embed)
        await interaction.response.send_message(f"Тикет создан! Перейдите в {channel.mention}")
        self.save_config()

    @app_commands.command(name="ticket_close", description="Закрыть тикет")
    async def close_ticket(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                "Эта команда может быть использована только в каналах тикетов!",
                ephemeral=True
            )

        await interaction.response.send_message("Тикет будет закрыт через 5 секунд...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(TicketSystem(bot)) 