# kafka-consumer-parquet

kafka topic 에서 데이터를 추출해 parquet 파일을 만들고 minio에 저장하는 서비스

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd kafka-consumer-parquet
poetry install --no-root
```

## History
+ 0.1.0: init
+ 0.1.1: data model 로 검증 하도록 수정(스키마 불일치 오류 방지)

python -m bytewax.run app
