import React from "react";
import { Button } from "react-bootstrap";

import API from "../../utils/API";

export class Logout extends React.Component {
  render() {
    return (
   <div className="toolbar__logout" id="btn_logout">
		<a  href="#">Logout</a>
        </div>
    );
  }
}
