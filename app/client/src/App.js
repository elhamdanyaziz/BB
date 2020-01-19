import React, { Component } from "react";
import { Route, Switch } from "react-router-dom";
import { Acceuil } from "./components/Acceuil/Acceuil.js";
import {Login} from "./components/Login/Login.js";
import { Signup } from "./components/Signup/Signup.js";
import { PrivateRoute } from "./components/PrivateRoute.js";
import "./App.css";
import Toolbar from "./components/Toolbar/Toolbar.js";

class App extends Component {
  render() {
    return (
      <div className="App">
        <Toolbar />
        <div className="App-content">
          <Switch>
            <Route exact path="/" component={Login} />
            <PrivateRoute path="/Acceuil" component={Acceuil} />
          </Switch>
        </div>
      </div>
    );
  }
}
export default App;
