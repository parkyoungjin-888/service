# fastapi-images-manager

images collection 을 관리하는 api 서버

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd fastapi-images-manager
poetry install --no-root
```

## History
+ 0.1.0: init, 재빌드
+ 0.1.1: data_model_module 이 utile_module 에 통합 후 적용, 스트리밍 추가
+ 0.1.2: 스트리밍 디바이스 선택이 적용 안되었던 버그 수정
+ 0.1.3: path 변경 적용 ( /list -> /many )
