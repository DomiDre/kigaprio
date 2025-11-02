/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "deleteRule": "@request.auth.id = userId || @request.auth.role = \"admin\"",
    "updateRule": "@request.auth.id = userId || @request.auth.role = \"admin\""
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "deleteRule": "@request.auth.id = userId",
    "updateRule": "@request.auth.id = userId"
  }, collection)

  return app.save(collection)
})
