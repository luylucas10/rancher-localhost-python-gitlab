from git import Repo
from yaml import safe_load, dump
from os import path
from argparse import ArgumentParser
from shutil import rmtree

def parse_arguments():
    """
    Analisa os argumentos da linha de comando.

    Retorna:
        argparse.Namespace: Argumentos da linha de comando analisados.
    """
    parser = ArgumentParser(description="Script para criar projeto Helm Chart no GitLab, baseado em um modelo, utilizando o prefixo '--namespace' no caminho do projeto")
    parser.add_argument("--repo_url", "-ru", required=True, help="URL do repositório")
    parser.add_argument("--user", "-us", required=True, help="Nome de usuário para autenticação Git")
    parser.add_argument("--token", "-tk", required=True, help="Token de acesso ao GitLab. Deve ter acesso completo na API")
    parser.add_argument("--charts_dir", "-td", required=True, help="Diretório temporário para clonar o repositório")
    parser.add_argument("--tag", required=True, help="Namespace de destino, utilizado no prefixo do caminho", default="charts")
    return parser.parse_args()

args = parse_arguments()

def clone_repo(repo_url, clone_dir, username, token):
    """
    Clona o repositório privado usando o token de acesso.

    Args:
        repo_url (str): URL do repositório a ser clonado.
        clone_dir (str): Diretório para clonar o repositório.
        username (str): Nome de usuário para autenticação.
        token (str): Token de acesso para autenticação.
    """
    # Constrói a URL de autenticação usando o token
    repo_url_with_token = repo_url.replace("https://", f"https://{username}:{token}@")

    # Clona o repositório se o diretório não existir
    if not path.exists(clone_dir):
        print(f"Clonando o repositório {repo_url} para {clone_dir}...")
        Repo.clone_from(repo_url_with_token, clone_dir)
    else:
        print(f"O diretório {clone_dir} já existe. Pulando clonagem.")

def update_image_tag(file_path, new_tag):
    """
    Atualiza a tag da imagem no arquivo YAML.

    Args:
        file_path (str): Caminho para o arquivo YAML.
        new_tag (str): Nova tag da imagem.
    """
    # Carrega o conteúdo do arquivo YAML
    with open(file_path, 'r') as file:
        content = safe_load(file)

    # Verifica se a chave 'image' existe e atualiza a tag
    if 'image' in content and 'tag' in content['image']:
        print(f"Atualizando a tag para: {new_tag}")
        content['image']['tag'] = new_tag
    else:
        print("Imagem ou tag não encontrada no arquivo YAML.")
        return

    # Escreve as alterações de volta no arquivo
    with open(file_path, 'w') as file:
        dump(content, file, default_flow_style=False, sort_keys=False)

def commit_and_push_changes(repo_dir, commit_message):
    """
    Faz commit e push das mudanças no repositório.

    Args:
        repo_dir (str): Diretório do repositório.
        commit_message (str): Mensagem do commit.
    """
    # Abre o repositório clonado
    repo = Repo(repo_dir)

    # Adiciona as mudanças
    repo.git.add(update=True)

    # Realiza o commit
    repo.index.commit(commit_message)

    # Faz o push das mudanças
    origin = repo.remote(name='origin')
    origin.push()

def main():
    """
    Função principal para clonar o repositório, atualizar a tag da imagem e enviar as mudanças.
    """
    values_file_path = path.join(args.charts_dir, 'values.yaml')
    clone_repo(args.repo_url, args.charts_dir, args.user, args.token)
    update_image_tag(values_file_path, args.tag)
    commit_and_push_changes(args.charts_dir, f"Atualizando a tag da imagem para {args.tag}")
    rmtree(args.charts_dir)
    print("Alterações enviadas com sucesso!")

if __name__ == '__main__':
    main()