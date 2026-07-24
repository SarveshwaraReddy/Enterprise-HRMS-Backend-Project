import pkg_resources

for dist in pkg_resources.working_set:
    print(f"{dist.project_name} {dist.version}")
