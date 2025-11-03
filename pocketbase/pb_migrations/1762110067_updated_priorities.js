/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_aORyEH3vd7` ON `priorities` (\n  `userId`,\n  `month`,\n  `identifier`\n)"
    ]
  }, collection)

  // add field
  collection.fields.addAt(2, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text1999537002",
    "max": 0,
    "min": 0,
    "name": "identifier",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_aORyEH3vd7` ON `priorities` (\n  `userId`,\n  `month`\n)"
    ]
  }, collection)

  // remove field
  collection.fields.removeById("text1999537002")

  return app.save(collection)
})
