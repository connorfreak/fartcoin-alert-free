import os
import ccxt
import pandas as pd
import time
from datetime import datetime
from gtts import gTTS
import io  # Untuk handle file di cloud

# Telegram (dari secrets)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Config
COINS = ["OGUSDT", "BONKUSDT", "PEPEUSDT", "FLOKIUSDT", "WIFUSDT"]
TIMEFRAME = "1h"
EMA_PERIOD = 21

# Init Bybit
bybit = ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

def check_ema_cross(symbol):
    try:
        ohlcv = bybit.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema21'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()
        
        current_price = df['close'].iloc[-1]
        ema21 = df['ema21'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        prev_ema21 = df['ema21'].iloc[-2]
        
        candle_time = datetime.fromtimestamp(df['timestamp'].iloc[-1]/1000).strftime("%Y-%m-%d %H:00")
        
        # Anti-spam: cek file flag (simpan di /tmp)
        flag_file = f"/tmp/{symbol}_{candle_time}.flag"
        if os.path.exists(flag_file):
            return
        
        # Deteksi cross/touch
        crossed_up = prev_close <= prev_ema21 and current_price > ema21
        crossed_down = prev_close >= prev_ema21 and current_price < ema21
        if crossed_up or crossed_down:
            direction = "NAIK" if crossed_up else "TURUN"
            text = f"🚨 {symbol} {direction} EMA-21 (1H)!\n💰 Harga: ${current_price:.6f}\n📊 EMA: ${ema21:.6f}\n⏰ {candle_time}"
            
            # Voice (simpan ke buffer, kirim via Telegram)
            voice_text = f"{symbol} harga {direction.lower()} EMA dua satu. Harga sekarang {current_price:.4f} dolar."
            tts = gTTS(text=voice_text, lang='id')
            voice_buffer = io.BytesIO()
            tts.write_to_fp(voice_buffer)
            voice_buffer.seek(0)
            
            # Kirim ke Telegram (text + voice)
            from telegram import Bot
            bot = Bot(token=TELEGRAM_TOKEN)
            bot.send_message(chat_id=CHAT_ID, text=text)
            bot.send_voice(chat_id=CHAT_ID, voice=voice_buffer, title=f"{symbol}_alert.mp3")
            
            # Buat flag anti-spam
            with open(flag_file, 'w') as f:
                f.write("sent")
            
            print(f"[ALERT] {symbol} - {direction} EMA-21 at {candle_time}")
            
    except Exception as e:
        print(f"[ERROR] {symbol}: {e}")

# Main loop (jalan 1x per run, cukup untuk cron-like)
for coin in COINS:
    check_ema_cross(coin)
print("FARTCOIN ALERT CHECK COMPLETED")
