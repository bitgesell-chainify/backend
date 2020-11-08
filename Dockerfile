FROM ubuntu

RUN apt-get update
RUN apt-get install -y wget
RUN mkdir .bitgesell
RUN cd .bitgesell
RUN wget https://bitgesell.ca/downloads/0.1.2/bitgesell_0.1.2_amd64.deb
RUN apt install -y ./bitgesell_0.1.2_amd64.deb
# CMD ["BGLd", "-server", "-rest"]

EXPOSE 8332 8454 8455 18332 18443 18454 18455 18474 18475