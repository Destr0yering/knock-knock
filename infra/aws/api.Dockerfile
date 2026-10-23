# Build ARM64 Python wheels on the native CloudShell architecture, then copy them
# into the Lambda ARM64 image without executing ARM64 build commands.
FROM --platform=linux/amd64 python:3.12-slim AS dependencies
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --target /asset \
    --platform manylinux2014_aarch64 \
    --implementation cp \
    --python-version 3.12 \
    --abi cp312 \
    --only-binary=:all: \
    ".[aws]"

FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.12
COPY --from=dependencies /asset/ ${LAMBDA_TASK_ROOT}/

CMD ["knock_knock.aws.api.handler"]
