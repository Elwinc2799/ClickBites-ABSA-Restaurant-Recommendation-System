import React from 'react';
import NavBar from '@/components/NavigationBar/NavBar';
import { Background } from '@/components/Background/Background';
import Footer from '@/components/Layout/Footer';
import axios from 'axios';
import { useState } from 'react';
import { toast } from 'react-toastify';
import { useRouter } from 'next/router';

function SignUp() {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [address, setAddress] = useState('');
    const [phone, setPhone] = useState('');
    const [state, setState] = useState('');
    const [city, setCity] = useState('');
    const [profilePic, setProfilePic] = useState<File | null>(null);
    const [message, setMessage] = useState('');
    const router = useRouter();

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
    
        if (password !== confirmPassword) {
            setMessage('Passwords do not match');
            toast('Passwords do not match', {
                hideProgressBar: true,
                autoClose: 2000,
                type: 'error',
                position: 'bottom-right',
            });
        } else {
            try {
                const formData = new FormData();
                formData.append('user', JSON.stringify({
                    name: name,
                    email: email,
                    password: password,
                    address: address,
                    phone: phone,
                    state: state,
                    city: city,
                }));

                // Append profile picture if it exists
                if (profilePic) {
                    formData.append('profile_pic', profilePic);
                }

                console.log(formData)
                
                // Send POST request with sign up form data to backend
                const response = await axios.post(
                    process.env.API_URL + '/api/signup',
                    formData,
                    { headers: { 'Content-Type': 'multipart/form-data' } }
                );
    
                setMessage(response.data.message);
                toast('Account created succesfully. Proceed to Log In.', {
                    hideProgressBar: true,
                    autoClose: 2000,
                    type: 'success',
                    position: 'bottom-right',
                });
    
                // Clear input boxes
                setName('');
                setEmail('');
                setPassword('');
                setConfirmPassword('');
                setAddress('');
                setPhone('');
                setState('');
                setCity('');
                setProfilePic(null);
    
                router.push('/login');
            } catch (error: any) {
                if (error.response) {
                    const responseData = error.response.data;
                    setMessage(responseData.message);
                    toast(responseData.message, {
                        hideProgressBar: true,
                        autoClose: 2000,
                        type: 'error',
                        position: 'bottom-right',
                    });
                } else {
                    setMessage('An unknown error occurred');
                    toast('An unknown error occured', {
                        hideProgressBar: true,
                        autoClose: 2000,
                        type: 'error',
                        position: 'bottom-right',
                    });
                }
            }
        }
    };    

    return (
        <>
            <NavBar isLanding={false} />
            <Background color="bg-gray-100">
                <div className="pb-24 pt-40 flex flex-col justify-center items-center">
                    <div className="w-1/3">
                        <div className="flex justify-center items-center">
                            <h1 className="text-3xl font-bold text-gray-800">
                                Sign Up
                            </h1>
                        </div>
                        <div className="flex justify-center items-center">
                            <form className="w-full" onSubmit={handleSubmit}>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="email">Email:</label>
                                    <input
                                        type="email"
                                        name="email"
                                        id="email"
                                        value={email}
                                        onChange={(event) =>
                                            setEmail(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="email">Name:</label>
                                    <input
                                        type="text"
                                        name="name"
                                        id="name"
                                        value={name}
                                        onChange={(event) =>
                                            setName(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="password">Password:</label>
                                    <input
                                        type="password"
                                        name="password"
                                        id="password"
                                        value={password}
                                        onChange={(event) =>
                                            setPassword(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="password">
                                        Confirm Password:
                                    </label>
                                    <input
                                        type="password"
                                        name="confirmPassword"
                                        id="confirmPassword"
                                        value={confirmPassword}
                                        onChange={(event) =>
                                            setConfirmPassword(
                                                event.target.value
                                            )
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="phone">Phone Number:</label>
                                    <input
                                        type="tel"
                                        name="phone"
                                        id="phone"
                                        value={phone}
                                        onChange={(event) =>
                                            setPhone(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="address">Address:</label>
                                    <input
                                        type="text"
                                        name="address"
                                        id="address"
                                        value={address}
                                        onChange={(event) =>
                                            setAddress(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="city">City:</label>
                                    <input
                                        type="text"
                                        name="city"
                                        id="city"
                                        value={city}
                                        onChange={(event) =>
                                            setCity(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="state">State:</label>
                                    <input
                                        type="text"
                                        name="state"
                                        id="state"
                                        value={state}
                                        onChange={(event) =>
                                            setState(event.target.value)
                                        }
                                        required
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-col my-4">
                                    <label htmlFor="profile_pic">Profile Picture:</label>
                                    <input
                                        type="file"
                                        accept="image/*"
                                        name="profile_pic"
                                        id="profile_pic"
                                        onChange={(event) => {
                                            if (event.target.files && event.target.files[0]) {
                                                setProfilePic(event.target.files[0]);
                                            }
                                        }}                  
                                        className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                    />
                                </div>
                                <div className="flex flex-row justify-end items-center">
                                    <button
                                        type="submit"
                                        className="btn bg-blue-500 hover:bg-blue-700 text-white rounded-md">
                                        Sign Up
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </Background>
            <Footer />
        </>
    );
}

export default SignUp;
