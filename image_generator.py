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
        card = Image.new('RGBA', (900, 280), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        
        # Создаем фон
        background = Image.new('RGBA', card.size, (0, 0, 0, 255))
        # Добавляем легкое размытие для эффекта глубины
        background = background.filter(ImageFilter.GaussianBlur(radius=20))
        card.paste(background, (0, 0))
        
        # Загружаем и обрабатываем аватар
        avatar = await self.download_avatar(str(user.display_avatar.url))
        avatar = avatar.resize((200, 200))
        
        # Создаем круглую маску для аватара
        mask = Image.new('L', avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 200, 200), fill=255)
        
        # Добавляем белую обводку вокруг аватара
        avatar_bg = Image.new('RGBA', (220, 220), (255, 255, 255, 255))
        avatar_bg_mask = Image.new('L', avatar_bg.size, 0)
        avatar_bg_draw = ImageDraw.Draw(avatar_bg_mask)
        avatar_bg_draw.ellipse((0, 0, 220, 220), fill=255)
        
        # Накладываем элементы
        card.paste(avatar_bg, (40, 30), avatar_bg_mask)
        card.paste(avatar, (50, 40), mask)
        
        # Добавляем текст
        draw = ImageDraw.Draw(card)
        
        # Имя пользователя
        draw.text((300, 50), user.name, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 48))
        
        # Уровень
        level_text = f"УРОВЕНЬ {level}"
        draw.text((300, 120), level_text, fill=(200, 200, 200), font=ImageFont.truetype("arial.ttf", 24))
        
        # Прогресс-бар
        progress = (xp / next_level_xp) * 100
        
        # Фон прогресс-бара
        draw.rectangle((300, 170, 800, 190), fill=(50, 50, 50))
        
        # Заполненная часть прогресс-бара
        gradient_width = int(500 * (progress/100))
        draw.rectangle((300, 170, 300 + gradient_width, 190), fill=(255, 255, 255))
        
        # XP текст
        xp_text = f"{xp:,} / {next_level_xp:,} XP"
        draw.text((300, 210), xp_text, fill=(200, 200, 200), font=ImageFont.truetype("arial.ttf", 20))
        
        # Сохраняем в буфер
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='rank.png')
        
    async def create_leaderboard_card(self, guild_name, leaders):
        # Создаем базовое изображение
        height = 200 + (len(leaders) * 100)
        card = Image.new('RGBA', (900, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(card)
        
        # Добавляем эффект свечения сверху
        gradient = Image.new('RGBA', (900, 100), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        for y in range(100):
            alpha = int(255 * (1 - y/100))
            gradient_draw.line((0, y, 900, y), fill=(255, 255, 255, alpha))
        card.paste(gradient, (0, 0), gradient)
        
        # Заголовок
        draw.text((50, 50), "ТАБЛИЦА ЛИДЕРОВ", fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 48))
        draw.text((50, 110), guild_name, fill=(200, 200, 200), font=ImageFont.truetype("arial.ttf", 24))
        
        # Добавляем каждого игрока
        for i, (user, level, xp) in enumerate(leaders):
            y = 200 + (i * 100)
            
            # Фон для строки (чередующийся)
            if i % 2 == 0:
                draw.rectangle((0, y, 900, y + 90), fill=(20, 20, 20))
            
            # Аватар
            try:
                avatar = await self.download_avatar(str(user.display_avatar.url))
                avatar = avatar.resize((70, 70))
                mask = Image.new('L', avatar.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 70, 70), fill=255)
                
                # Белая обводка для аватара
                avatar_bg = Image.new('RGBA', (80, 80), (255, 255, 255, 255))
                avatar_bg_mask = Image.new('L', avatar_bg.size, 0)
                avatar_bg_draw = ImageDraw.Draw(avatar_bg_mask)
                avatar_bg_draw.ellipse((0, 0, 80, 80), fill=255)
                
                card.paste(avatar_bg, (50, y + 5), avatar_bg_mask)
                card.paste(avatar, (55, y + 10), mask)
            except:
                pass
            
            # Позиция
            position_text = f"#{i+1}"
            draw.text((150, y + 30), position_text, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 32))
            
            # Имя пользователя
            draw.text((250, y + 20), user.name, fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 32))
            
            # Уровень и XP
            stats_text = f"УРОВЕНЬ {level}  •  {xp:,} XP"
            draw.text((250, y + 55), stats_text, fill=(200, 200, 200), font=ImageFont.truetype("arial.ttf", 20))
        
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='leaderboard.png')
        
    async def create_welcome_card(self, member, guild):
        # Создаем базовое изображение
        card = Image.new('RGBA', (900, 400), (0, 0, 0, 255))
        draw = ImageDraw.Draw(card)
        
        # Добавляем эффект свечения
        gradient = Image.new('RGBA', (900, 400), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        for y in range(400):
            alpha = int(50 * (1 - abs(y-200)/200))
            gradient_draw.line((0, y, 900, y), fill=(255, 255, 255, alpha))
        card.paste(gradient, (0, 0))
        
        # Загружаем и обрабатываем аватар
        avatar = await self.download_avatar(str(member.display_avatar.url))
        avatar = avatar.resize((200, 200))
        mask = Image.new('L', avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 200, 200), fill=255)
        
        # Белая обводка для аватара
        avatar_bg = Image.new('RGBA', (220, 220), (255, 255, 255, 255))
        avatar_bg_mask = Image.new('L', avatar_bg.size, 0)
        avatar_bg_draw = ImageDraw.Draw(avatar_bg_mask)
        avatar_bg_draw.ellipse((0, 0, 220, 220), fill=255)
        
        # Накладываем аватар (по центру)
        avatar_x = (900 - 220) // 2
        card.paste(avatar_bg, (avatar_x, 40), avatar_bg_mask)
        card.paste(avatar, (avatar_x + 10, 50), mask)
        
        # Добавляем текст
        welcome_text = "ДОБРО ПОЖАЛОВАТЬ"
        welcome_font = ImageFont.truetype("arial.ttf", 48)
        name_font = ImageFont.truetype("arial.ttf", 36)
        
        # Измеряем размеры текста
        welcome_bbox = draw.textbbox((0, 0), welcome_text, font=welcome_font)
        welcome_width = welcome_bbox[2] - welcome_bbox[0]
        
        name_bbox = draw.textbbox((0, 0), member.name, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        
        # Рисуем текст по центру
        draw.text(
            ((900 - welcome_width) // 2, 290),
            welcome_text,
            fill=(255, 255, 255),
            font=welcome_font
        )
        
        draw.text(
            ((900 - name_width) // 2, 350),
            member.name,
            fill=(200, 200, 200),
            font=name_font
        )
        
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename='welcome.png') 