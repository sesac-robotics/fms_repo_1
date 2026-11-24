# syntax=docker/dockerfile:1
FROM maven:3.9.12-eclipse-temurin-21@sha256:c3c9d3ac4ce8431a3995c0318b8d390f448e693dd4fabc16e9b68d2e1f3d7b46 AS java-build
WORKDIR /build
COPY Server/AMOMainServer/AmoMainControlService/ Server/AMOMainServer/AmoMainControlService/
COPY Server/AMOMainServer/AmoDB/migrations/ Server/AMOMainServer/AmoDB/migrations/
COPY Server/WebServer/AmoWebService/backend/ Server/WebServer/AmoWebService/backend/

FROM java-build AS main-build
RUN --mount=type=cache,target=/root/.m2,sharing=locked mvn -B -ntp -f Server/AMOMainServer/AmoMainControlService/pom.xml spotless:check verify

FROM java-build AS gateway-build
RUN --mount=type=cache,target=/root/.m2,sharing=locked mvn -B -ntp -f Server/WebServer/AmoWebService/backend/pom.xml spotless:check verify

FROM eclipse-temurin:21-jre@sha256:d77e090ae1f6970c047b443c6f0a6c1358b0426d44432bb5a7753408cd43de0d AS java-runtime
WORKDIR /app
USER 10001:10001
ENTRYPOINT ["java", "-jar", "/app/service.jar"]

FROM java-runtime AS main-control
COPY --from=main-build /build/Server/AMOMainServer/AmoMainControlService/target/amo-main-control-0.1.0-SNAPSHOT.jar /app/service.jar

FROM java-runtime AS gateway
COPY --from=gateway-build /build/Server/WebServer/AmoWebService/backend/target/amo-web-service-0.1.0-SNAPSHOT.jar /app/service.jar

FROM node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94 AS admin-web
WORKDIR /app
RUN chown node:node /app
USER node
COPY --chown=node:node Server/WebServer/AmoWebService/frontend/admin/package*.json ./
RUN npm ci --no-audit --no-fund
COPY --chown=node:node Server/WebServer/AmoWebService/frontend/admin/ ./
RUN npm test && npm run build
CMD ["npm", "run", "dev", "--", "--strictPort"]
