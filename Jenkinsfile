pipeline {
    agent any

    stages {
        stage('Checkout Code') {
            steps {
                // Pulls the latest code directly from your GitHub repository
                checkout scm
            }
        }
        
        stage('Build Backend Container') {
            steps {
                // Navigates to the backend folder and builds the Docker image
                dir('backend') {
                    sh 'docker build -t twitter-backend:latest .'
                }
            }
        }
        
        stage('Build Frontend Container') {
            steps {
                // Navigates to the frontend folder and builds the Docker image
                dir('frontend') {
                    sh 'docker build -t twitter-frontend:latest .'
                }
            }
        }
        
        stage('DevSecOps Vulnerability Scan') {
            steps {
                // This is where we will add Trivy to scan for CVEs (Sun Life requirement)
                echo 'Executing security scan on Docker images...'
            }
        }
        
        stage('Publish Artifacts') {
            steps {
                // This is where we will push the images to Artifactory (Sun Life requirement)
                echo 'Pushing verified, secure images to artifact repository...'
            }
        }
    }
}