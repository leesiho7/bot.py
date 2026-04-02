import os
import time
import numpy as np
import pandas as pd
from datetime import datetime
from okx.MarketData import MarketAPI

# [인증 설정] Railway Variables에 등록한 값들을 가져옴
API_KEY = os.getenv("OKX_API_KEY", "your_key")
API_SECRET = os.getenv("OKX_API_SECRET", "your_secret")
PASSPHRASE = os.getenv("OKX_PASSPHRASE", "your_pass")
FLAG = "0" # 실계좌

# [전략 설정]
SYMBOLS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP", "DOGE-USDT-SWAP"]
REG_LENGTH = 100
STD_DEV_MULT = 2.0
FUNDING_THRESHOLD = 0.0003 # 0.03% 과열 기준

# OKX API 초기화
market_api = MarketAPI(API_KEY, API_SECRET, PASSPHRASE, False, FLAG)

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def calculate_lin_reg(df, length, n_std):
    """DonovanWall 선형 회귀 채널 계산"""
    y = df['close'].tail(length).values
    x = np.arange(length)
    
    slope, intercept = np.polyfit(x, y, 1)
    current_reg = (slope * (length - 1)) + intercept
    
    # 오차에 대한 표준편차 계산
    reg_line_full = (slope * x) + intercept
    std_dev = np.std(y - reg_line_full)
    
    upper = current_reg + (std_dev * n_std)
    lower = current_reg - (std_dev * n_std)
    return current_reg, upper, lower, slope

def monitor_markets():
    log("🚀 [System] Dober Monitor v1.0 가동 시작 (Mean Reversion)")
    log(f"📋 감시 종목: {', '.join(SYMBOLS)}")
    
    while True:
        for symbol in SYMBOLS:
            try:
                # 1. 15분봉 데이터 수집
                res = market_api.get_candlesticks(instId=symbol, bar='15m', limit=150)
                if not res or 'data' not in res:
                    continue
                    
                df = pd.DataFrame(res['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v', 'vccy', 'vccyq', 'confirm'])
                df['close'] = df['c'].astype(float)
                
                # 2. 지표 계산
                reg_line, upper, lower, slope = calculate_lin_reg(df, REG_LENGTH, STD_DEV_MULT)
                current_price = df['close'].iloc[-1]
                
                # 3. 실시간 펀딩비 조회
                funding_res = market_api.get_funding_rate(instId=symbol)
                funding_rate = float(funding_res['data'][0]['fundingRate'])
                
                # 4. 상태 브리핑 (Railway 로그에서 확인 가능)
                dist_pct = ((current_price - upper) / upper) * 100
                log(f"🔍 [{symbol[:4]}] {current_price:.2f} | 상단대비:{dist_pct:+.2f}% | 펀딩비:{funding_rate:.4%}")

                # 5. 타점 포착 (AI 없이 로그만 남김)
                if current_price > upper and funding_rate >= FUNDING_THRESHOLD:
                    log(f"🚨🚨 [타점 포착] {symbol} 과열! 채널 돌파 및 펀딩비 {funding_rate:.4%} 도달!")
                    # 여기서 나중에 주문 함수(execute_order)를 호출하면 됨
                
            except Exception as e:
                log(f"⚠️ {symbol} 분석 중 오류: {e}")
            
            time.sleep(1.5) # API 속도 제한 방지
        
        time.sleep(10) # 한 사이클 후 휴식

if __name__ == "__main__":
    monitor_markets()
