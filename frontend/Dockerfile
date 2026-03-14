# lightweight Node.js image to keep container size small
FROM node:18-alpine

# set the working directory inside the container
WORKDIR /app

# copy package files first to leverage Docker cache
COPY package.json package-lock.json* ./

# install Node.js dependencies
RUN npm install

# copy rest of the frontend source code into the container
COPY . .

# expose port 3000 for the React application
EXPOSE 3000

# run the React application
CMD ["npm", "start"]