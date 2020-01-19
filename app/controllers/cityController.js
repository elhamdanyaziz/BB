const User = require("../../schema/schemaCity.js");


async function createcity(req, res) {

  const { name } = req.body;

  const city = {
    name

  };

  try {

    const cityData = new City(city);
    const cityObject = await cityData.save();
    return res.status(200).json({
      text: "Succès",
      token: cityData.getToken()
    });
  } catch (error) {
    return res.status(500).json({ error });
  }
}

module.exports = function(app) {
  app.post("/city", createcity);
};
