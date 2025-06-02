# spark-image-consumer

kafka topic 에서 image 데이터를 받아 mongodb와 minio에 저장하는 서비스

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd spark-image-consumer
poetry install --no-root
```

## History
+ v0.1.0: init
+ v0.1.1: mongo 저장 시 insort 를 upsert 로 변경
+ v0.1.2: 미사용 파일 삭제
