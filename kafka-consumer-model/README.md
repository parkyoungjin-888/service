# kafka-consumer-model

kafka topic 에서 입력 받아 모델을 적용 하고 결과를 저장 하는 서비스

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd kafka-consumer-model
poetry install --no-root
```

## History
+ 0.1.0: init
+ 0.1.1: 베이스 이미지 변경
+ 0.1.2: 베이스 이미지에 python 설치 추가
+ 0.1.3: kafka 모듈 업데이트 적용 (컨슈머 비동기 콜백 예외 처리)
