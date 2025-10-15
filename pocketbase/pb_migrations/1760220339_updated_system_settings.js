/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // update collection data
  unmarshal({
    "createRule": "",
    "updateRule": "@request.auth.role = \"admin\"",
    "viewRule": ""
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // update collection data
  unmarshal({
    "createRule": null,
    "updateRule": null,
    "viewRule": null
  }, collection)

  return app.save(collection)
})
