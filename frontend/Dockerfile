# 빌드 스테이지
FROM node:20-alpine AS builder

WORKDIR /app

# package.json 복사 및 의존성 설치
COPY package.json package-lock.json* ./
RUN npm install

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# 프로덕션 스테이지
FROM nginx:alpine

# nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/nginx.conf

# 빌드 결과물 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# 포트 노출
EXPOSE 80

# nginx 실행
CMD ["nginx", "-g", "daemon off;"]
