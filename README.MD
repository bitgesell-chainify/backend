
# Chainify Bitgesell mobile wallet backend

In order to get access to data please attach API key to you reauest header
```x-api-key: Ty1HRTEuG57HVWFta94j37FCO8X9D43A2ftOoG4y```


API endpoint to get list of transactions by wallet address

[https://bitgesell.amrbz.org/v1/address/bgl1ql5pn7scxzuwmetkw0n84jhv6md0rt2t409kvpl](https://bitgesell.amrbz.org/v1/address/bgl1ql5pn7scxzuwmetkw0n84jhv6md0rt2t409kvpl)

Output:
![Image of responce output](https://colivka.s3.eu-central-1.amazonaws.com/Screenshot+2020-11-08+at+16.52.57.png)


The parsing engine guarantees to calculate accout balcancee properly.

[https://bitgesell.amrbz.org/v1/address/bgl1qnuy5y59t7whymvfjc9tcn8gyjf0l0qs37v39sw](https://bitgesell.amrbz.org/v1/address/bgl1qnuy5y59t7whymvfjc9tcn8gyjf0l0qs37v39sw)


![Image of responce output](https://colivka.s3.eu-central-1.amazonaws.com/Screenshot+2020-11-08+at+16.55.20.png)

![Image of responce output](https://colivka.s3.eu-central-1.amazonaws.com/Screenshot+2020-11-08+at+16.55.51.png)

The backend architecture uses AWS serverless solutions (Lambda, API Gateway, Load balancing) to handle client requests. That allows to scale the app userbase and forget about server archistration.