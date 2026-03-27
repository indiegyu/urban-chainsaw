-- Ghost 전용 MySQL DB 초기화 (docker-compose 최초 실행 시 자동 실행)
-- PostgreSQL n8n DB와 분리하여 운영
CREATE DATABASE IF NOT EXISTS ghost CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON ghost.* TO 'ghost'@'%';
FLUSH PRIVILEGES;
