"""Ког с командами автомодерации."""

import re

import discord
from discord import app_commands
from discord.ext import commands


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="automod", description="Настройка автомодерации")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod(
        self,
        interaction: discord.Interaction,
        action: str,
        value: str | None = None,
    ):
        action = action.lower()
        automod_service = self.bot.automod

        if action == "addword" and value:
            if value not in automod_service.config["banned_words"]:
                automod_service.config["banned_words"].append(value)
                automod_service.save_config()
                await interaction.response.send_message(
                    f"Слово '{value}' добавлено в список запрещенных",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Это слово уже в списке", ephemeral=True
                )

        elif action == "removeword" and value:
            if value in automod_service.config["banned_words"]:
                automod_service.config["banned_words"].remove(value)
                automod_service.save_config()
                await interaction.response.send_message(
                    f"Слово '{value}' удалено из списка запрещенных",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Этого слова нет в списке", ephemeral=True
                )

        elif action == "listwords":
            if automod_service.config["banned_words"]:
                words = "\n".join(automod_service.config["banned_words"])
                await interaction.response.send_message(
                    f"Запрещенные слова:\n```\n{words}\n```",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Список запрещенных слов пуст", ephemeral=True
                )

        elif action == "setspam" and value:
            try:
                threshold = int(value)
                if 1 <= threshold <= 20:
                    automod_service.config["spam_threshold"] = threshold
                    automod_service.save_config()
                    await interaction.response.send_message(
                        f"Порог спама установлен на {threshold} сообщений",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Значение должно быть от 1 до 20", ephemeral=True
                    )
            except ValueError:
                await interaction.response.send_message(
                    "Требуется числовое значение", ephemeral=True
                )

        elif action == "setinterval" and value:
            try:
                interval = int(value)
                if 1 <= interval <= 60:
                    automod_service.config["spam_interval"] = interval
                    automod_service.save_config()
                    await interaction.response.send_message(
                        f"Интервал спама установлен на {interval} секунд",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Значение должно быть от 1 до 60", ephemeral=True
                    )
            except ValueError:
                await interaction.response.send_message(
                    "Требуется числовое значение", ephemeral=True
                )

        elif action == "setmentions" and value:
            try:
                mentions = int(value)
                if 1 <= mentions <= 10:
                    automod_service.config["max_mentions"] = mentions
                    automod_service.save_config()
                    await interaction.response.send_message(
                        f"Лимит упоминаний установлен на {mentions}",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Значение должно быть от 1 до 10", ephemeral=True
                    )
            except ValueError:
                await interaction.response.send_message(
                    "Требуется числовое значение", ephemeral=True
                )

        elif action == "setwarnings" and value:
            try:
                warnings = int(value)
                if 1 <= warnings <= 10:
                    automod_service.config["max_warnings"] = warnings
                    automod_service.save_config()
                    await interaction.response.send_message(
                        f"Максимум предупреждений установлен на {warnings}",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Значение должно быть от 1 до 10", ephemeral=True
                    )
            except ValueError:
                await interaction.response.send_message(
                    "Требуется числовое значение", ephemeral=True
                )

        elif action == "setmute" and value:
            if re.match(r"^\d+[mhd]$", value):
                automod_service.config["mute_duration"] = value
                automod_service.save_config()
                await interaction.response.send_message(
                    f"Длительность мута установлена на {value}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Неверный формат. Используйте число + m/h/d (например: 30m, 1h, 7d)",
                    ephemeral=True,
                )

        else:
            await interaction.response.send_message(
                "Неверная команда или отсутствует значение", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AutoModCog(bot))

