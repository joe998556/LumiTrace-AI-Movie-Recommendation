# LumiTrace Android v1.0.6

This release fixes a release-build JSON parsing crash that could show:

`java.lang.Class cannot be cast to java.lang.reflect.ParameterizedType`

## Fixes

- Switched the BERT recommendation response path to raw JSON parsing instead of release-minified Retrofit/Gson generic conversion.
- Removed the watched-movie local cache dependency on Gson `TypeToken`.
- Keeps the v1.0.5 MovieLens hybrid recommender request format:
  - watched movie IDs
  - user ratings
  - genre metadata
  - release year hints

## Recommended Action

Install `LumiTrace-v1.0.6-release.apk` if v1.0.5 shows a `ParameterizedType` error on the recommendation page.
