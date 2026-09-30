FROM public.ecr.aws/lambda/python:3.12

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . --target "${LAMBDA_TASK_ROOT}"

CMD ["knock_knock.aws.api.handler"]
