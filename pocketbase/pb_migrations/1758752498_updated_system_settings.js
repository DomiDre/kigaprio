/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // update collection data
  unmarshal({
    "listRule": "@request.auth.role = \"service\"",
    "viewRule": null
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // update collection data
  unmarshal({
    "listRule": null,
    "viewRule": "@request.auth.role = \"service\""
  }, collection)

  return app.save(collection)
})
