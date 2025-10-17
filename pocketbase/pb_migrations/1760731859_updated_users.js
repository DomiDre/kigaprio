/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // remove field
  collection.fields.removeById("select4220459851")

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // add field
  collection.fields.addAt(12, new Field({
    "hidden": false,
    "id": "select4220459851",
    "maxSelect": 1,
    "name": "security_tier",
    "presentable": false,
    "required": true,
    "system": false,
    "type": "select",
    "values": [
      "high",
      "balanced",
      "convenience"
    ]
  }))

  return app.save(collection)
})
