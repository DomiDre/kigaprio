/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // add field
  collection.fields.addAt(5, new Field({
    "hidden": false,
    "id": "bool282836676",
    "name": "manual",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // remove field
  collection.fields.removeById("bool282836676")

  return app.save(collection)
})
