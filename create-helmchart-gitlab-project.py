from os import path, walk
from shutil import rmtree
from gitlab import Gitlab, exceptions
from git import Repo
from argparse import ArgumentParser
from yaml import safe_load

def parse_arguments():
    """
    Analisa os argumentos da linha de comando.

    Retorna:
        argparse.Namespace: Argumentos da linha de comando analisados.
    """
    parser = ArgumentParser(description="Script para criar projeto Helm Chart no GitLab, baseado em um modelo, utilizando o prefixo '--namespace' no caminho do projeto")
    parser.add_argument("--gitlab_url", "-g", required=True, help="URL da instância do GitLab")
    parser.add_argument("--user", "-u", required=True, help="Nome de usuário para autenticação Git")
    parser.add_argument("--token", "-t", required=True, help="Token de acesso ao GitLab. Deve ter acesso completo na API")
    parser.add_argument("--source_project", "-src", required=True, help="URL do projeto fonte")
    parser.add_argument("--source_dir", "-sd", required=True, help="Diretório do projeto fonte")
    parser.add_argument("--model_repo", "-m", required=True, help="URL do repositório modelo")
    parser.add_argument("--namespace", "-n", required=True, help="Namespace de destino, utilizado no prefixo do caminho", default="charts")
    parser.add_argument("--charts_dir", "-td", required=True, help="Diretório temporário para clonar o repositório modelo de helm chart")
    parser.add_argument("--tekton_result_repo_url", "-tr", required=True, help="Variável de ambiente para armazenar o resultado da execução")
    return parser.parse_args()

args = parse_arguments()

# Inicializa a instância do GitLab
gl = Gitlab(args.gitlab_url, private_token=args.token)

def get_or_create_group(group_name, parent_id=None):
    """
    Recupera ou cria um grupo no GitLab.

    Args:
        group_name (str): Nome do grupo.
        parent_id (int, opcional): ID do grupo pai. Padrão é None.

    Retorna:
        gitlab.v4.objects.Group: O grupo recuperado ou criado.
    """
    try:
        groups = gl.groups.list(search=group_name, all=True)
        for group in groups:
            if group.name.lower() == group_name.lower() and (group.parent_id == parent_id or parent_id is None):
                print(f"Grupo '{group_name}' encontrado.")
                return group
        group = gl.groups.create({
            'name': group_name,
            'path': group_name,
            'parent_id': parent_id
        })
        print(f"Grupo '{group_name}' criado.")
    except exceptions.GitlabCreateError as e:
        print(f"Erro ao criar o grupo '{group_name}': {e}")
        raise
    return group

def create_project_in_target_namespace(source_url):
    """
    Cria um projeto no namespace de destino.

    Args:
        source_url (str): URL do projeto fonte.

    Retorna:
        tuple: O projeto criado e um booleano indicando se o projeto é novo.
    """
    path_parts = source_url.replace(args.gitlab_url + "/", "").split("/")
    parent_id = None
    for part in [args.namespace] + path_parts[:-1]:
        group = get_or_create_group(part, parent_id)
        parent_id = group.id

    project_name = path_parts[-1].replace(".git", "")
    try:
        project_path = f"{args.namespace}/{'/'.join(path_parts[:-1])}/{project_name}"
        project = gl.projects.get(project_path)
        print(f"Projeto '{project_name}' já existe.")
        with open(args.tekton_result_repo_url, 'w') as f:
            f.write(project.http_url_to_repo)
        return project, False  # Retorna False, pois o projeto já existe
    except exceptions.GitlabGetError:
        project = gl.projects.create({
            'name': project_name,
            'namespace_id': parent_id,
            'path': project_name
        })
        print(f"Projeto '{project_name}' criado em '{project_path}'.")
        with open(args.tekton_result_repo_url, 'w') as f:
            f.write(project.http_url_to_repo)
    return project, True  # Retorna True, pois o projeto foi criado e precisa ser populado

def clone_repo(repo_url, target_dir, user, token):
    """
    Clona um repositório privado usando o nome de usuário e token de acesso.

    Args:
        repo_url (str): URL do repositório a ser clonado.
        target_dir (str): Diretório para clonar o repositório.
        user (str): Nome de usuário para autenticação.
        token (str): Token de acesso para autenticação.

    Retorna:
        git.Repo: O repositório clonado.
    """
    # Insere o nome de usuário e token na URL para autenticação
    auth_url = repo_url.replace("https://", f"https://{user}:{token}@")
    return Repo.clone_from(auth_url, target_dir)

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

def replace_tags(file_path, replacements):
    """
    Substitui as tags no arquivo especificado.

    Args:
        file_path (str): Caminho para o arquivo.
        replacements (dict): Dicionário de tags e seus valores de substituição.
    """
    with open(file_path, 'r') as file:
        content = file.read()

    for tag, value in replacements.items():
        content = content.replace(tag, value)

    with open(file_path, 'w') as file:
        file.write(content)

def replace_tags_in_directory(directory, replacements):
    """
    Substitui tags em todos os arquivos do diretório especificado.

    Args:
        directory (str): Caminho para o diretório.
        replacements (dict): Dicionário de tags e seus valores de substituição.
    """
    for root, _, files in walk(directory):
        for file_name in files:
            if file_name.endswith(".yaml"):
                file_path = path.join(root, file_name)
                replace_tags(file_path, replacements)

def main():
    """
    Função principal para criar o projeto e populá-lo com templates, se necessário.
    """
    # Criação do projeto e verificação se é necessário popular com templates
    project, is_new_project = create_project_in_target_namespace(args.source_project)

    if is_new_project:
        try:
            # Repositório temporário para armazenar os arquivos do modelo
            if path.exists(args.charts_dir):
                print(f"Removendo diretório existente: {args.charts_dir}")
                rmtree(args.charts_dir)

            # Clona o repositório de código-fonte
            print("Clonando o repositório modelo...")
            clone_repo(args.model_repo, args.charts_dir, args.user, args.token)

            # Inicializa o repositório de destino (não precisa de Repo.init() aqui, já que foi clonado)
            print("Configurando o repositório de destino...")

            # Substitui o remote 'origin' com a URL do repositório de destino
            repo = Repo(args.charts_dir)

            # abrir arquivo .cicd.yaml para realizar a leitura do projectName e appName
            try:
                with open(path.join(args.source_dir, ".cicd.yaml"), 'r') as file:
                    content = safe_load(file)
                    replacements = {
                        "<<PROJECT_NAME>>": content["project"],
                        "<<APP_NAME>>": content["app"],
                    }
            except FileNotFoundError:
                print("Erro: Arquivo .cicd.yaml não encontrado no diretório do código-fonte.")
                exit(1)

            replace_tags_in_directory(args.charts_dir, replacements)

            # Substitui o remote existente (origin) pela nova URL
            target_url = project.http_url_to_repo.replace("https://", f"https://{args.user}:{args.token}@")
            try:
                repo.remotes.origin.set_url(target_url)
                print("URL do remote 'origin' atualizada para o repositório de destino.")
            except IndexError:
                # Se o remote 'origin' não existir, cria um novo
                print("Remote 'origin' criado com a URL do repositório de destino.")
                repo.create_remote('origin', target_url)

            # Adiciona e faz commit das mudanças
            commit_message = "Inicialização o projeto com manifestos modelo."
            print("Fazendo commit e push para o repositório de destino...")
            commit_and_push_changes(args.charts_dir, commit_message)

            # Limpa o diretório temporário
            rmtree(args.charts_dir)
            print("Processo concluído. Projeto criado com manifestos modelo.")
        finally:
            if path.exists(args.charts_dir):
                rmtree(args.charts_dir)
                print("Limpeza: diretório temporário removido.")
    else:
        print("O projeto já existe. Nenhuma ação adicional será tomada.")

if __name__ == "__main__":
    main()