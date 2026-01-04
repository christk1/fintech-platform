resource "aws_s3_bucket" "origin" {
	bucket = var.bucket_name
}

resource "aws_cloudfront_distribution" "this" {
	enabled = true

	origin {
		domain_name = aws_s3_bucket.origin.bucket_regional_domain_name
		origin_id   = "s3-origin"
	}

	default_cache_behavior {
		target_origin_id       = "s3-origin"
		viewer_protocol_policy = "allow-all"

		allowed_methods = ["GET", "HEAD"]
		cached_methods  = ["GET", "HEAD"]

		forwarded_values {
			query_string = false

			cookies {
				forward = "none"
			}
		}
	}

	restrictions {
		geo_restriction {
			restriction_type = "none"
		}
	}

	viewer_certificate {
		cloudfront_default_certificate = true
	}
}
