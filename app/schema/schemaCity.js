const mongoose = require("mongoose");
const jwt = require("jwt-simple");
const config = require("../config/config");

const citySchema = mongoose.Schema(
  {
    email: {
      type: String,
      lowercase: true,
      trim: true,
      unique: true,
      required: true
    },
  },
  { timestamps: { createdAt: "created_at" } }
);


module.exports = mongoose.model("City", citySchema);
