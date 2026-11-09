# infra-TAK ETL catalog

The list of CloudTAK ETLs that [infra-TAK](https://github.com/takwerx/infra-TAK) can install and
run on its local ETL Runner (no AWS account needed).

- **COE ETLs:** every `etl-*` repository of [dfpc-coe](https://github.com/dfpc-coe), at its newest
  release tag (`etl-base` and `etl-template` are libraries, not ETLs).
- **Community ETLs:** ETLs from other authors. Each one has its own name prefix, so it never
  collides with a COE ETL.

Each entry is pinned to a **commit SHA**. An infra-TAK server builds the ETL from exactly that
commit. A new ETL, or a new version of one, gets a security review before its entry is marked
`reviewed`. infra-TAK does not install an entry that has no review.

## How an infra-TAK server uses this repository

When the ETL Runner is on, the server checks this repository once a day (or when you click
**Check now** on the CloudTAK page).

1. It reads the current commit of `main`, then reads `catalog.json` and `catalog.json.sig` at
   that commit.
2. It verifies the Ed25519 signature in `catalog.json.sig` over the exact bytes of
   `catalog.json`. The public key is part of infra-TAK itself
   (`modules/etlrunner/catalog_signing.pub`). The private key is kept offline. It is not on
   GitHub and not in CI.
3. It refuses a catalog with a lower `serial` than the one it already has.
4. If anything fails, the server keeps the catalog it already has. Every infra-TAK release also
   includes a copy of the catalog.

A change to this repository that is not signed with the offline key has no effect on any server.

## Adding a community ETL

Open an issue with the repository URL and the release tag or commit you want listed. The ETL
must be a standard CloudTAK ETL (built on `@tak-ps/etl`, with a `Dockerfile` and
`capabilities.json`), and it must pass the security review before it is listed.

## Files

| File | What it is |
|---|---|
| `catalog.json` | The catalog: `schema`, `serial`, and one entry per ETL (`prefix`, `name`, `description`, `source`, `ref`, `sha`, `version`, `author`, `flags`, `reviewed`, …). Names and descriptions come from each ETL's own `capabilities.json`. |
| `catalog.json.sig` | Base64 Ed25519 signature over the exact bytes of `catalog.json`. |

## License

MIT for this catalog data. Each ETL has its own license in its own repository.
