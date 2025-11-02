/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // update collection data
  unmarshal({
    "createRule": null,
    "viewRule": "@request.auth.role = \"service\" || @request.auth.role = \"admin\""
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // update collection data
  unmarshal({
    "createRule": "",
    "viewRule": ""
  }, collection)

  return app.save(collection)
})
