# Usar uma imagem base com Python
FROM python:3.12-alpine

# Instala o Git
RUN apk add --no-cache git

# Define a variável de ambiente USER_ID
ARG USER_ID

# Caso não seja passado, usar 1000 como valor padrão
ENV USER_ID=${USER_ID:-1000}

# Cria o usuário com o ID dinâmico
RUN adduser -D -u ${USER_ID} appuser

# Define o diretório de trabalho no container
WORKDIR /app

# Copia o script Python para o container
COPY create-helmchart-gitlab-project.py update-helmchart-gitlab-project.py requirements.txt ./

# Instala a biblioteca python-gitlab
RUN pip install --no-cache-dir -r requirements.txt

# Altera as permissões para o usuário correto
RUN chown -R appuser:appuser /app

# Muda para o usuário criado
USER appuser
