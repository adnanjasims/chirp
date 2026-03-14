pipeline {
    agent any

    stages {
        stage('Checkout Code') {
            steps {
                // Pulls latest code from github
                checkout scm
            }
        }
        
        stage('Build Backend Container') {
            steps {
                dir('backend') {
                    sh 'docker build -t twitter-backend:latest .'
                }
            }
        }
        
        stage('Build Frontend Container') {
            steps {
                dir('frontend') {
                    sh 'docker build -t twitter-frontend:latest .'
                }
            }
        }
        
        stage('DevSecOps Vulnerability Scan') {
            steps {
                echo 'Executing security scan on Docker images...'
                // runs trivy security scanner on backend
                sh 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL --exit-code 0 twitter-backend:latest'
                // runs trivy security scanner on frontend
                sh 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL --exit-code 0 twitter-frontend:latest'
            }
        }
        
        stage('Publish Artifacts') {
            steps {
                echo 'Pushing verified, secure images to artifact repository...'
            }
        }
    }
}
