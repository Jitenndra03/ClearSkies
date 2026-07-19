import { Component } from 'react';

/**
 * Error Boundary — wraps page routes to catch render errors.
 * Shows last-known-good data from cache, or a directive empty state.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, retryCount: 0 };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ClearSkies ErrorBoundary]', error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, retryCount: this.state.retryCount + 1 });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <div className="error-fallback-icon">⚠</div>
          <div className="error-fallback-title">Something went wrong</div>
          <div className="error-fallback-message">
            Unable to load this page. Check your connection and try again.
          </div>
          <button className="btn btn-primary" onClick={this.handleRetry}>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
