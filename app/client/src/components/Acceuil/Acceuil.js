import React from "react";
import { Button } from "react-bootstrap";

import API from "../../utils/API";

const API_KEY = "5a002cc70279599365e51d612b81bf50";


export class Acceuil extends React.Component {
  disconnect = () => {
    API.logout();
    window.location = "/";
  };

   getWeather = async (e) => {
    e.preventDefault();
    const city = e.target.elements.city.value;
    const api_call = await fetch(`http://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${API_KEY}&units=metric&lang=fr);
    const data = await api_call.json();
    if (city && country) {
      this.setState({
        temperature: data.main.temp,
        city: data.name,
        country: data.sys.country,
        humidity: data.main.humidity,
        description: data.weather[0].description,
        error: ""
      });
    } else {
      this.setState({
        temperature: undefined,
        city: undefined,
        country: undefined,
        humidity: undefined,
        description: undefined,
        error: "Please enter the values."
      });
    }
  }


  render() {
    return (
       <div className="toolbar__logout" id="btn_logout">
		        <Button onClick={this.disconnect}  type="submit">
          Logout
        </Button>



		  <div className="card-body">
                  <Form getWeather={this.getWeather} />
                  <Weather 
                    temperature={this.state.temperature} 
                    humidity={this.state.humidity}
                    city={this.state.city}
                    country={this.state.country}
                    description={this.state.description}
                    error={this.state.error}
                  />

		  </div>
        </div>


    );
  }
}
