// ---------------------------
// セグメントLEDアニメーション用
// ---------------------------

void setup() {
  // デジタルピン出力設定
  DDRD |= B11111100;  // D2〜D7 を出力
  DDRB |= B00001111;  // D8〜D11 を出力

  // 7セグLEDコモン端子の初期値
  PORTB &= ~(1 << 2);  // D10 = LOW
  PORTB &= ~(1 << 3);  // D11 = LOW

  // シリアル通信
  Serial.begin(115200);
  // Serial.begin(9600);
  Serial.println("Arduino Ready");
}

#define ANIME_CAPACITY 300
#define DIGIT_COUNT 2
#define REFRESH_MS 1  // ダイナミック点灯のデフォルト周期 (Memo: 1msec より長くできるが通信への影響が不明）

// 桁ごとの点灯パターン（[anim][digit], [1]:10の桁, [0]:1の桁）
uint8_t digitPatterns[ANIME_CAPACITY][DIGIT_COUNT] = {
  {B01000110, B01110000},
  {B00111001, B00001111},
  {B00000000, B00000000}
};

// アニメパターン切り替え間隔（msec）
uint16_t animeFrames[ANIME_CAPACITY] = {360, 600, 950};

// アニメパターンごとのチラつき周期（usec）
uint16_t flickerDelays[ANIME_CAPACITY] = {15, 25, 0};

// 登録アニメパターン数
uint16_t animeCount = 3;

int activeAnimeIndex = 0;
int activeDigitIndex = 0;

int prevMillis = 0; 
int animeTime = 0;

// ---------------------------
// 関数
// ---------------------------
void setActiveDigit(int index){
  // index = 0 → 1の桁を点灯,　index = 10 → 10の桁を点灯
  PORTB &= B11110011; // 全桁reset
  PORTB |= (1 << (2 + index));  // 選択桁のみON
}

void loop() {
  // シリアル通信
  if(Serial.available() >= 2){
    uint8_t timeHigh = Serial.read(); // 上位ビット
    uint8_t timeLow = Serial.read(); // 下位ビット
    uint16_t ptnLen = (timeHigh << 8) | timeLow;
    animeCount = ptnLen;
    for(int i = 0; i < ptnLen; i++){
      while(Serial.available() < 6){;}
      uint8_t pattern10 = Serial.read();
      uint8_t pattern01 = Serial.read();
      timeHigh = Serial.read(); // 上位ビット
      timeLow = Serial.read(); // 下位ビット
      uint16_t duration = (timeHigh << 8) | timeLow;
      timeHigh = Serial.read(); // 上位ビット
      timeLow = Serial.read(); // 下位ビット
      uint16_t flickeDelay = (timeHigh << 8) | timeLow;

      digitPatterns[i][0] = pattern10;
      digitPatterns[i][1] = pattern01;
      animeFrames[i] = duration;
      flickerDelays[i] = flickeDelay;
      Serial.write("R");  // ハンドシェイク
    }
  }

  // アニメパターン切り替え
  animeTime += millis() - prevMillis;
  prevMillis = millis();
  if(animeTime > animeFrames[activeAnimeIndex]){
    activeAnimeIndex = (activeAnimeIndex + 1) % animeCount;
    animeTime = 0;
  }

  // ---------------------------
  // コモン端子の切り替え
  // ---------------------------
  activeDigitIndex = (activeDigitIndex + 1) % 2;
  setActiveDigit(activeDigitIndex);

  // ---------------------------
  // セグメント点灯
  // ---------------------------
  PORTD &=  B00000011;              // D2〜D7 以外をクリア
  PORTD |=  (digitPatterns[activeAnimeIndex][activeDigitIndex] << 2);

  PORTB &=  B11111100;              // D8,D9 以外をクリア
  PORTB |=  (digitPatterns[activeAnimeIndex][activeDigitIndex] >> 6);

  delay(REFRESH_MS + flickerDelays[activeAnimeIndex]);
}
