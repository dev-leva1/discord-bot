from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
import discord
import os

class ImageGenerator:
    def __init__(self):
        self.font_path = "fonts"
        os.makedirs(self.font_path, exist_ok=True)
        
    async def download_avatar(self, avatar_url):
        response = requests.get(avatar_url)
        return Image.open(BytesIO(response.content))
        
    async def create_rank_card(self, user, level, xp, next_level_xp):
        # Создаем базовое изображение
        card = Image.new('RGBA', (800, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        
        # Загружаем аватар
        avatar = await self.download_avatar(str(user.display_avatar.url))
        avatar = avatar.resize((180, 180))
        
        # Создаем маску для круглого аватара
        mask = Image.new('L', avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 180, 180), fill=255)
        
        # Добавляем фон с градиентом
        gradient = Image.new('RGBA', card.size)
        gradient_draw = ImageDraw.Draw(gradient)
        gradient_draw.rectangle((0, 0, 800, 240), fill=(47, 49, 54, 255))
        
        # Накладываем элементы
        card.paste(gradient, (0, 0))
        card.paste(avatar, (30, 30), mask)
        
        # Добавляем текст
        draw = ImageDraw.Draw(card)
        draw.text((240, 40), user.name, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 36))
        draw.text((240, 90), f"Уровень: {level}", fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 28))
        
        # Прогресс-бар
        progress = (xp / next_level_xp) * 100
        draw.rectangle((240, 150, 740, 180), fill=(47, 49, 54))
        draw.rectangle((240, 150, 240 + (500 * (progress/100)), 180), fill=(114, 137, 218))
        draw.text((240, 190), f"XP: {xp}/{next_level_xp}", fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 24))
        
        # Сохраняем в буфер
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='rank.png')
        
    async def create_leaderboard_card(self, guild_name, leaders):
        # Создаем базовое изображение
        height = 150 + (len(leaders) * 100)
        card = Image.new('RGBA', (800, height), (47, 49, 54, 255))
        draw = ImageDraw.Draw(card)
        
        # Заголовок
        draw.text((40, 30), f"Таблица лидеров - {guild_name}", fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 36))
        
        # Добавляем каждого игрока
        for i, (user, level, xp) in enumerate(leaders):
            y = 120 + (i * 100)
            
            # Аватар
            try:
                avatar = await self.download_avatar(str(user.display_avatar.url))
                avatar = avatar.resize((80, 80))
                mask = Image.new('L', avatar.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 80, 80), fill=255)
                card.paste(avatar, (40, y), mask)
            except:
                pass
                
            # Медали
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
            draw.text((140, y), medal, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 36))
            
            # Информация
            draw.text((200, y), user.name, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 32))
            draw.text((200, y+40), f"Уровень: {level} • XP: {xp}", fill=(180, 180, 180), font=ImageFont.truetype("arial.ttf", 24))
            
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='leaderboard.png')
        
    async def create_welcome_card(self, member, guild):
        # Создаем базовое изображение
        card = Image.new('RGBA', (800, 300), (47, 49, 54, 255))
        draw = ImageDraw.Draw(card)
        
        # Загружаем и обрабатываем аватар
        avatar = await self.download_avatar(str(member.display_avatar.url))
        avatar = avatar.resize((200, 200))
        mask = Image.new('L', avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 200, 200), fill=255)
        
        # Добавляем элементы
        card.paste(avatar, (300, 20), mask)
        
        # Текст
        draw.text((400-len(member.name)*7, 240), f"Добро пожаловать,", fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 36))
        draw.text((400-len(member.name)*7, 240), f"\n{member.name}!", fill=(114, 137, 218), font=ImageFont.truetype("arial.ttf", 36))
        
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='welcome.png') 