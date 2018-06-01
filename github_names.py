from subprocess import check_output

contributors = sorted(set(x.strip('"') for x in check_output(
    ['git', 'log', '--format="%aN <%aE>"']
).decode("utf-8").splitlines()))


with open('.github-map') as fh:
    github_map_lines = fh.read().strip().split('\n')


github_map = {}

for line in github_map_lines:
    username, contributor_name = line.split('|')
    username = username.strip()
    contributor_name = contributor_name.strip()
    if username:
        github_map[contributor_name] = username


for contributor in contributors:
    if contributor not in github_map:
        print(contributor)

