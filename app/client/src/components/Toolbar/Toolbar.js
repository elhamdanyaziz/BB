import React from "react";

import logo from '../../img/logo.png';
import './Toolbar.css';

const toolbar = props => (
  <header className="toolbar">
    <nav className="toolbar__navigation">
        
        <div className="toolbar__logo">
		<img src={logo}/>
		<p>
		   Meteo App
		</p>
        </div>

     
    </nav>
  </header>
);

export default toolbar;
  
  
