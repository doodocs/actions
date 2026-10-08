# release-gitops-tag

Writes a new image tag into a GitOps repository (Helm values or a kustomization) the way
argocd-image-updater used to, but driven by CI and with guard rails:

- refuses to write a tag lower than the current one (`sort -V`), unless `ALLOW_DOWNGRADE: "true"`;
- optionally verifies the image tag exists in the registry before writing (`IMAGE` + registry creds);
- edits exactly one line of the file (quotes, comments and list indentation stay untouched) and aborts otherwise;
- commits as `github-actions[bot]` with the source repo, SHA, run URL and actor in the message;
- pushes with rebase-and-retry, re-checking the guard after every rebase;
- `DRY_RUN: "true"` prints the diff without committing.

```yaml
- uses: doodocs/actions/release-gitops-tag@main
  with:
    REPOSITORY: doodocs/yc-apps
    TOKEN: ${{ secrets.GITOPS_TOKEN }}        # contents:write on the GitOps repo
    FILE: doodocs-kedo/values-prod.yaml
    YAML_PATH: .image.tag
    NEW_TAG: ${{ needs.prepare.outputs.version }}
    IMAGE: cr.yandexcloud.kz/<registry>/doodocs-kedo:${{ needs.prepare.outputs.version }}
    REGISTRY_USERNAME: json_key
    REGISTRY_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
```

Why: Yandex Cloud Registry returns only the first 10 tags of `tags/list` without a `Link` header,
so argocd-image-updater picks a stale "newest" tag and downgrades production (ENG-8585, 08.10.2026).
