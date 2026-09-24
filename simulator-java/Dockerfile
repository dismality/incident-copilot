FROM maven:3.9.9-eclipse-temurin-21-alpine AS build
WORKDIR /workspace

COPY pom.xml ./
RUN mvn -q -B dependency:go-offline

COPY src ./src
RUN mvn -q -B verify

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S incidentcopilot && adduser -S incidentcopilot -G incidentcopilot
WORKDIR /app

COPY --from=build /workspace/target/incident-copilot-simulator-0.1.0.jar app.jar
USER incidentcopilot
EXPOSE 8081

ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
