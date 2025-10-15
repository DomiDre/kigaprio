/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // remove field
  collection.fields.removeById("number3501145981")

  // remove field
  collection.fields.removeById("json3654893783")

  // remove field
  collection.fields.removeById("text1269603864")

  // remove field
  collection.fields.removeById("text826688707")

  // add field
  collection.fields.addAt(3, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text3396753604",
    "max": 0,
    "min": 0,
    "name": "encrypted_fields",
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

  // add field
  collection.fields.addAt(3, new Field({
    "hidden": false,
    "id": "number3501145981",
    "max": null,
    "min": null,
    "name": "weekNumber",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  // add field
  collection.fields.addAt(4, new Field({
    "hidden": false,
    "id": "json3654893783",
    "maxSize": 0,
    "name": "priorities",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  // add field
  collection.fields.addAt(5, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text1269603864",
    "max": 0,
    "min": 0,
    "name": "startDate",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(6, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text826688707",
    "max": 0,
    "min": 0,
    "name": "endDate",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  // remove field
  collection.fields.removeById("text3396753604")

  return app.save(collection)
})
