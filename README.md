# Nome do Projeto

## Descrição
Este repositório contém scripts para automatizar a criação e atualização de projetos Helm Chart no GitLab. O projeto utiliza um repositório modelo para criar novos projetos de Helm Chart, seguindo a árvore de grupos e subgrupos existentes, e atualiza as tags de imagens nos manifestos.

## Funcionalidades
- Criação de projetos Helm Chart no GitLab com base em um repositório modelo.
- Atualização das tags de imagens em arquivos `values.yaml`.
- Suporte para substituição de tags personalizadas em arquivos YAML.

## Scripts
### create-helmchart-gitlab-project.py
Este script cria um repositório de Helm Charts baseado em outro repositório modelo, seguindo a árvore de grupos e subgrupos presentes no repositório inicial. Além disso, substitui as tags `<<PROJECT_NAME>>` e `<<APP_NAME>>` com valores baseados em um arquivo `.cicd.yaml`.

### update-helmchart-gitlab-project.py
Este script clona um repositório de manifestos e substitui o valor da tag da imagem no arquivo `values.yaml`.

## Requisitos
As dependências necessárias para este projeto estão listadas no arquivo `requirements.txt`:

```
certifi==2024.8.30
charset-normalizer==3.4.0
click==8.1.7
gitdb==4.0.11
GitPython==3.1.43
idna==3.10
markdown-it-py==3.0.0
mdurl==0.1.2
Pygments==2.18.0
python-gitlab==5.0.0
PyYAML==6.0.2
requests==2.32.3
requests-toolbelt==1.0.0
shellingham==1.5.4
smmap==5.0.1
typing_extensions==4.12.2
urllib3==2.2.3
```

## Imagem de Container
A imagem de container utilizada para este projeto está baseada no Python 3.12 e inclui o Git. Abaixo está o Dockerfile utilizado:

```dockerfile
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

# Copia os scripts Python para o container
COPY create-helmchart-gitlab-project.py update-helmchart-gitlab-project.py requirements.txt ./

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Altera as permissões para o usuário correto
RUN chown -R appuser:appuser /app

# Muda para o usuário criado
USER appuser
```

## Uso
### create-helmchart-gitlab-project.py
Para executar o script `create-helmchart-gitlab-project.py`, utilize o seguinte comando:

```bash
python create-helmchart-gitlab-project.py \
  --gitlab_url <GITLAB_URL> \
  --user <USERNAME> \
  --token <TOKEN> \
  --source_project <SOURCE_PROJECT> \
  --source_dir <SOURCE_DIR> \
  --model_repo <MODEL_REPO> \
  --namespace <NAMESPACE> \
  --charts_dir <CHARTS_DIR> \
  --tekton_result_repo_url <TEKTON_RESULT_REPO_URL>
  
```

### update-helmchart-gitlab-project.py
Para executar o script `update-helmchart-gitlab-project.py`, utilize o seguinte comando:

```bash
python update-helmchart-gitlab-project.py \
  --repo_url <REPO_URL> \
  --user <USERNAME> \
  --token <TOKEN> \
  --charts_dir <CHARTS_DIR> \
  --tag <TAG>
```

## Contribuição
Contribuições são bem-vindas!

## Licença
Este projeto está licenciado sob a Licença MIT.
