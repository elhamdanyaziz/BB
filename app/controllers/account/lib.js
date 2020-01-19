const User = require("../../schema/schemaUser.js");
const passwordHash = require("password-hash");

async function signup(req, res) {
  console.log(req.body);

  const { password, email } = req.body;
  if (!email || !password) {

    return res.status(400).json({
      text: "Requête invalide"
    });
  }

  const user = {
    email,
    password: passwordHash.generate(password)
  };

  try {
    const findUser = await User.findOne({
      email
    });
    if (findUser) {
      return res.status(400).json({
        text: "L'utilisateur existe déjà"
      });
    }
  } catch (error) {
    return res.status(500).json({ error });
  }
  try {

    const userData = new User(user);
    const userObject = await userData.save();
    return res.status(200).json({
      text: "Succès",
      token: userObject.getToken()
    });
  } catch (error) {
    return res.status(500).json({ error });
  }
}

async function login(req, res) {
  const { password, email } = req.body;
  if (!email || !password) {

    return res.status(400).json({
      text: "Requête invalide"
    });
  }
  try {

    const findUser = await User.findOne({ email });
    if (!findUser)
      return res.status(401).json({
        text: "L'utilisateur n'existe pas"
      });
    if (!findUser.authenticate(password))
      return res.status(401).json({
        text: "Mot de passe incorrect"
      });
    return res.status(200).json({
      token: findUser.getToken(),
      text: "Authentification réussi"
    });
  } catch (error) {
    return res.status(500).json({
      error
    });
  }
}



exports.login = login;
exports.signup = signup;
