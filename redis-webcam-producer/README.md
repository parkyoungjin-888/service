# redis-webcam-producer

webcam 이미지 취득 후 redis stream 으로 전달하는 서비스

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd redis-webcam-producer
poetry install --no-root
```

## History
+ v0.1.0: init, 서비스명 변경 ( agent-webcam-stream -> redis-webcam-producer )
+ v0.1.1: 도커 베이스 이미지를 arm 용 이미지로 변경
+ v0.1.2: 0.1.1 취소
+ v0.1.3: device_id 추가
