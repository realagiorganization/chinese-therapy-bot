terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.98"
    }

    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }

    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.49"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

provider "azuread" {
  tenant_id = var.azure_tenant_id
}

provider "aws" {
  region = var.aws_region
}
