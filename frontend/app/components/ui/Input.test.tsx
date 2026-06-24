import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from './Input';
import { describe, it, expect, vi } from 'vitest';

describe('Input', () => {
  it('renders a basic input', () => {
    render(<Input data-testid="test-input" />);
    expect(screen.getByTestId('test-input')).toBeInTheDocument();
  });

  it('renders with a label', () => {
    render(<Input label="My Label" />);
    expect(screen.getByLabelText('My Label')).toBeInTheDocument();
  });

  it('displays a value and handles onChange', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    
    // To test onChange, we need a stateful component
    const TestComponent = () => {
      const [value, setValue] = React.useState('test');
      const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setValue(e.target.value);
        handleChange(e);
      };
      return <Input label="My Label" value={value} onChange={onChange} />;
    };
    render(<TestComponent />);
    
    const input = screen.getByLabelText('My Label');
    expect(input).toHaveValue('test');

    await user.type(input, 'ing');
    expect(handleChange).toHaveBeenCalledTimes(3);
    expect(input).toHaveValue('testing');
  });
  
  it('updates value correctly when controlled', async () => {
    const user = userEvent.setup();
    const TestComponent = () => {
      const [value, setValue] = React.useState('');
      return <Input label="My Label" value={value} onChange={e => setValue(e.target.value)} />;
    };
    render(<TestComponent />);

    const input = screen.getByLabelText('My Label');
    expect(input).toHaveValue('');
    await user.type(input, 'new value');
    expect(input).toHaveValue('new value');
  });

  it('displays an error message', () => {
    render(<Input error="This is an error" />);
    expect(screen.getByText('This is an error')).toBeInTheDocument();
  });

  it('applies error styles when error prop is present', () => {
    render(<Input error="This is an error" label="My Label" />);
    expect(screen.getByLabelText('My Label')).toHaveClass('border-error');
  });
  
  it('applies custom className', () => {
    render(<Input className="my-custom-class" label="My Label" />);
    expect(screen.getByLabelText('My Label')).toHaveClass('my-custom-class');
  });
  
  it('forwards other input props', () => {
    render(<Input placeholder="Enter text..." disabled />);
    const input = screen.getByPlaceholderText('Enter text...');
    expect(input).toBeInTheDocument();
    expect(input).toBeDisabled();
  });
});
