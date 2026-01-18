"""Модуль для генерации изображений для Discord бота."""

import os
from io import BytesIO

import discord
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
import asyncio

class ImageGenerator:
    """Класс для генерации различных изображений."""
    
    def __init__(self):
        """Инициализация генератора изображений."""
        self.font_path = os.path.join("assets", "fonts")
        os.makedirs(self.font_path, exist_ok=True)
        
    async def download_avatar(self, avatar_url: str) -> Image.Image:
        """Загрузка аватара пользователя.
        
        Args:
            avatar_url: URL аватара
            
        Returns:
            Image.Image: Загруженное изображение
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                data = await resp.read()
        return await asyncio.to_thread(Image.open, BytesIO(data))
        
    async def create_rank_card(
        self,
        user: discord.User,
        level: int,
        xp: int,
        next_level_xp: int
    ) -> discord.File:
        """Создание карточки ранга пользователя.
        
        Args:
            user: Пользователь
            level: Текущий уровень
            xp: Текущий опыт
            next_level_xp: Опыт для следующего уровня
            
        Returns:
            discord.File: Сгенерированная карточка
        """
        def generate_card():
            card = Image.new('RGBA', (900, 280), (0, 0, 0, 0))
            draw = ImageDraw.Draw(card)
            background = Image.new('RGBA', card.size, (0, 0, 0, 255))
            background = background.filter(ImageFilter.GaussianBlur(radius=20))
            card.paste(background, (0, 0))
            return card
        card = await asyncio.to_thread(generate_card)
        
        avatar = await self.download_avatar(str(user.display_avatar.url))
        avatar = avatar.resize((200, 200))
        
        mask = Image.new('L', avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 200, 200), fill=255)
        
        avatar_bg = Image.new('RGBA', (220, 220), (255, 255, 255, 255))
        avatar_bg_mask = Image.new('L', avatar_bg.size, 0)
        avatar_bg_draw = ImageDraw.Draw(avatar_bg_mask)
        avatar_bg_draw.ellipse((0, 0, 220, 220), fill=255)
        
        card.paste(avatar_bg, (40, 30), avatar_bg_mask)
        card.paste(avatar, (50, 40), mask)
        
        draw = ImageDraw.Draw(card)
        
        await asyncio.to_thread(draw.text, (300, 50), user.name, (255, 255, 255), ImageFont.truetype("arial.ttf", 48))
        
        level_text = f"УРОВЕНЬ {level}"
        await asyncio.to_thread(draw.text, (300, 120), level_text, (200, 200, 200), ImageFont.truetype("arial.ttf", 24))
        
        progress = (xp / next_level_xp) * 100
        
        await asyncio.to_thread(draw.rectangle, (300, 170, 800, 190), (50, 50, 50))
        
        gradient_width = int(500 * (progress/100))
        await asyncio.to_thread(draw.rectangle, (300, 170, 300 + gradient_width, 190), (255, 255, 255))
        
        xp_text = f"{xp:,} / {next_level_xp:,} XP"
        await asyncio.to_thread(draw.text, (300, 210), xp_text, (200, 200, 200), ImageFont.truetype("arial.ttf", 20))
        
        buffer = BytesIO()
        await asyncio.to_thread(card.save, buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='rank.png')
        
    async def create_leaderboard_card(
        self,
        guild_name: str,
        leaders: list[tuple[discord.User, int, int]]
    ) -> discord.File:
        """Создание карточки таблицы лидеров."""
        # Download avatars asynchronously first
        avatars = []
        for user, _, _ in leaders:
            try:
                avatar = await self.download_avatar(str(user.display_avatar.url))
            except Exception:
                avatar = None
            avatars.append(avatar)
        def generate_leaderboard():
            height = 200 + (len(leaders) * 100)
            card = Image.new('RGBA', (900, height), (0, 0, 0, 255))
            draw = ImageDraw.Draw(card)
            gradient = Image.new('RGBA', (900, 100), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient)
            for y in range(100):
                alpha = int(255 * (1 - y/100))
                gradient_draw.line((0, y, 900, y), fill=(255, 255, 255, alpha))
            card.paste(gradient, (0, 0), gradient)
            draw.text((50, 50), "ТАБЛИЦА ЛИДЕРОВ", fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 48))
            draw.text((50, 110), guild_name, fill=(200, 200, 200), font=ImageFont.truetype("arial.ttf", 24))
            for i, (user, level, xp) in enumerate(leaders):
                y = 200 + (i * 100)
                if i % 2 == 0:
                    draw.rectangle((0, y, 900, y + 90), fill=(20, 20, 20))
                avatar = avatars[i]
                if avatar is not None:
                    avatar = avatar.resize((70, 70))
                    mask = Image.new('L', avatar.size, 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, 70, 70), fill=255)
                    avatar_bg = Image.new('RGBA', (80, 80), (255, 255, 255, 255))
                    avatar_bg_mask = Image.new('L', avatar_bg.size, 0)
                    avatar_bg_draw = ImageDraw.Draw(avatar_bg_mask)
                    avatar_bg_draw.ellipse((0, 0, 80, 80), fill=255)
                    card.paste(avatar_bg, (50, y + 5), avatar_bg_mask)
                    card.paste(avatar, (55, y + 10), mask)
                position_text = f"#{i+1}"
                draw.text((150, y + 30), position_text, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 32))
                draw.text((250, y + 20), user.name, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 32))
                stats_text = f"УРОВЕНЬ {level}  •  {xp:,} XP"
                draw.text((250, y + 55), stats_text, fill=(200, 200, 200), font=ImageFont.truetype("arial.ttf", 20))
            buffer = BytesIO()
            card.save(buffer, format='PNG')
            buffer.seek(0)
            return discord.File(buffer, filename='leaderboard.png')
        return await asyncio.to_thread(generate_leaderboard)
        
    async def create_welcome_card(
        self,
        member: discord.Member,
        guild: discord.Guild
    ) -> discord.File:
        """Создание карточки приветствия.
        
        Args:
            member: Новый участник
            guild: Сервер
            
        Returns:
            discord.File: Сгенерированная карточка
        """
        def generate_card():
            card = Image.new('RGBA', (900, 400), (0, 0, 0, 255))
            draw = ImageDraw.Draw(card)
            gradient = Image.new('RGBA', (900, 400), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient)
            for y in range(400):
                alpha = int(50 * (1 - abs(y-200)/200))
                gradient_draw.line((0, y, 900, y), fill=(255, 255, 255, alpha))
            card.paste(gradient, (0, 0))
            return card
        card = await asyncio.to_thread(generate_card)
        
        avatar = await self.download_avatar(str(member.display_avatar.url))
        avatar = avatar.resize((200, 200))
        mask = Image.new('L', avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 200, 200), fill=255)
        
        avatar_bg = Image.new('RGBA', (220, 220), (255, 255, 255, 255))
        avatar_bg_mask = Image.new('L', avatar_bg.size, 0)
        avatar_bg_draw = ImageDraw.Draw(avatar_bg_mask)
        avatar_bg_draw.ellipse((0, 0, 220, 220), fill=255)
        
        avatar_x = (900 - 220) // 2
        card.paste(avatar_bg, (avatar_x, 40), avatar_bg_mask)
        card.paste(avatar, (avatar_x + 10, 50), mask)
        
        welcome_text = "ДОБРО ПОЖАЛОВАТЬ"
        welcome_font = ImageFont.truetype("arial.ttf", 48)
        name_font = ImageFont.truetype("arial.ttf", 36)
        draw = ImageDraw.Draw(card)
        welcome_bbox = draw.textbbox((0, 0), welcome_text, font=welcome_font)
        welcome_width = welcome_bbox[2] - welcome_bbox[0]
        name_bbox = draw.textbbox((0, 0), member.name, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text(((900 - welcome_width) // 2, 290), welcome_text, fill=(255, 255, 255), font=welcome_font)
        draw.text(((900 - name_width) // 2, 350), member.name, fill=(200, 200, 200), font=name_font)
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='welcome.png') 
