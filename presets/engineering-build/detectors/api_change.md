# Detector: api_change

Decide whether the feature adds or changes an API. Read `spec.md`, `plan.md` and `data-model.md` if it exists.

**Yes signals:** user stories that name a client calling a service, new or changed endpoints, webhooks or public integrations, a UI that needs new server data, an existing OpenAPI file in the repo that the feature touches.

**No signals:** the feature changes only internal code, dependency versions, build or CI files, documentation or purely client-side behavior.

**Unknown:** the evidence points both ways.

Note the API style if it is not REST or GraphQL (gRPC, event contracts); the adapter skips those with a warning.

Output exactly:

```
result: yes | no | unknown
style: rest | graphql | grpc | events | unspecified
evidence:
  - "<quoted line>"
```
