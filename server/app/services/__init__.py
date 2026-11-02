# ==============================================================================
# File: server/app/services/__init__.py
# Purpose: Marks the services folder as a Python sub-package.
#
# NOTE: Intentionally does not eagerly re-export from sub-modules to avoid
#       circular import issues (workflows → services → workflows). Consumers
#       should import directly from the specific service module they need.
# ==============================================================================
