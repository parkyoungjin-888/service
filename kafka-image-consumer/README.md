# kafka-image-consumer

kafka topic 에서 이미지를 입력 받아 mongodb 및 minio에 저장하는 서비스

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd kafka-image-consumer
poetry install --no-root
```

## History
+ 0.1.0: init
+ 0.1.1: bytewax 을 사용한 스트리밍 구조로 수정, github action 변경 후 재빌드2
+ 0.1.2: images data model 에 updated_datetime 추가 반영
+ 0.1.3: 폴링 적용

python -m bytewax.run app
