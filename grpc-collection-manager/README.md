# grpc-collection-manager

mongodb collection을 관리 할 수 있는 grpc 서버 서비스

## Index

- [Installation](#installation)
- [History](#History)

## Installation

Instructions for setting up the project.

```bash
# Clone the repository
git clone https://github.com/parkyoungjin-888/service.git

# Install dependencies using Poetry
cd grpc-collection-manager
poetry install --no-root
```

## History
+ 0.1.0: init 
+ 0.1.1: data_model_module 버전업 0.1.3
+ 0.1.2: doc_id 로 update, delete 불가능 했던 오류 수정
+ 0.1.3: 로그 데코레이터 적용
+ 0.1.4: 모듈 경로 변경, 데이터 모델 모듈 업데이트
+ 0.1.5: data_model 다운로드 방식으로 수정
+ 0.1.6: UpdateOne DeleteOne 추가
+ 0.1.7: UpdateOne 및 UpdateMany 타입 변환 기능 미적용 버그 수정
+ 0.1.8: data model을 캐쉬로 사용 하지 않도록 수정
