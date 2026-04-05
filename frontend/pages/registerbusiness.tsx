import React, {
    useState,
    ChangeEvent,
    FormEvent,
    useContext,
    useEffect,
} from 'react';
import NavBar from '@/components/NavigationBar/NavBar';
import { Background } from '@/components/Background/Background';
import Footer from '@/components/Layout/Footer';
import axios from 'axios';
import { toast } from 'react-toastify';
import { useRouter } from 'next/router';
import { getCookie } from 'cookies-next';
import { LocationContext } from '@/components/utils/LocationContext';
import dynamic from 'next/dynamic';
const MapComponent = dynamic(() => import('@/components/Map/MapComponent'), { ssr: false });

interface Business {
    name: string;
    address: string;
    city: string;
    state: string;
    categories: string;
    description: string;
    hours: Record<string, string>;
}

function RegisterBusiness() {
    // Get default location from context
    const { latitude: defaultLatitude, longitude: defaultLongitude } =
        useContext(LocationContext);

    console.log(defaultLatitude, defaultLongitude);

    const defaultCenter = {
        lat: defaultLatitude || 0,
        lng: defaultLongitude || 0,
    };

    const [selectedLocation, setSelectedLocation] = useState(defaultCenter);

    // Set default location to context
    useEffect(() => {
        const newCenter = {
            lat: defaultLatitude || 0,
            lng: defaultLongitude || 0,
        };

        setSelectedLocation(newCenter);
    }, [defaultLatitude, defaultLongitude]);

    const initialBusinessState: Business = {
        name: '',
        address: '',
        city: '',
        state: '',
        categories: '',
        description: '',
        hours: {
            Monday: '',
            Tuesday: '',
            Wednesday: '',
            Thursday: '',
            Friday: '',
            Saturday: '',
            Sunday: '',
        },
    };

    const [business, setBusiness] = useState<Business>(initialBusinessState);
    const [businessPic, setBusinessPic] = useState<File | null>(null);

    const [latitude, setLatitude] = useState<number | null>(defaultLatitude);
    const [longitude, setLongitude] = useState<number | null>(defaultLongitude);

    const router = useRouter();

    // Handle business registration form input changes
    const handleInputChange = (
        e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => {
        const { name, value } = e.target;
        setBusiness({ ...business, [name]: value });
    };

    const handleHoursChange = (e: ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setBusiness({
            ...business,
            hours: { ...business.hours, [name]: value },
        });
    };

    // Handle business registration form submission
    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        const formData = new FormData();

        if (businessPic) {
            formData.append('business_pic', businessPic);
        }

        // Add latitude and longitude to business object
        const businessWithLocation = {
            ...business,
            latitude: latitude,
            longitude: longitude,
        };

        formData.append('business', JSON.stringify(businessWithLocation));

        console.log(formData);

        try {
            // Send POST request with form data to backend
            const response = await axios.post(
                process.env.API_URL + '/api/business',
                formData,
                {
                    headers: {
                        Authorization: `Bearer ${getCookie('token')}`,
                    },
                    withCredentials: true,
                }
            );

            if (response.status !== 200) {
                throw new Error('Error creating business');
            } else {
                toast('Business created succesfully. ', {
                    hideProgressBar: true,
                    autoClose: 2000,
                    type: 'success',
                    position: 'bottom-right',
                });

                // Clear form after submission
                setBusiness(initialBusinessState);
                setBusinessPic(null);

                router.push('/dashboard');
            }
        } catch (error: any) {
            if (error.response) {
                const responseData = error.response.data;
                toast(responseData.message, {
                    hideProgressBar: true,
                    autoClose: 2000,
                    type: 'error',
                    position: 'bottom-right',
                });
            } else {
                toast('An unknown error occured', {
                    hideProgressBar: true,
                    autoClose: 2000,
                    type: 'error',
                    position: 'bottom-right',
                });
            }
        }
    };

    return (
        <>
            <NavBar isLanding={false} />
            <Background color="bg-gray-100">
                <div className="pb-24 pt-28 flex flex-col justify-center items-center">
                    <div className="w-full px-20">
                        <div className="flex justify-center items-center">
                            <h1 className="text-3xl font-bold text-gray-800">
                                Register Business
                            </h1>
                        </div>
                        <div className="flex justify-center items-center">
                            <form className="w-full" onSubmit={handleSubmit}>
                                <div className="flex flex-row">
                                    <div className="flex flex-col my-4 w-1/2">
                                        <label htmlFor="name">
                                            Business Name:
                                        </label>
                                        <input
                                            id="name"
                                            name="name"
                                            type="text"
                                            className="mb-4 border-2 border-gray-300 p-2 rounded-md focus:outline-none mr-4"
                                            placeholder="Name"
                                            value={business.name}
                                            onChange={handleInputChange}
                                            required
                                        />
                                        <label htmlFor="address">
                                            Address:
                                        </label>
                                        <input
                                            id="address"
                                            name="address"
                                            type="text"
                                            className="mb-4 border-2 border-gray-300 p-2 rounded-md focus:outline-none mr-4"
                                            placeholder="Address"
                                            value={business.address}
                                            onChange={handleInputChange}
                                            required
                                        />
                                        <div className="flex flex-row mb-4 justify-between">
                                            <div className="flex flex-col w-1/2 pr-4">
                                                <label htmlFor="city">
                                                    City:
                                                </label>
                                                <input
                                                    id="city"
                                                    name="city"
                                                    type="text"
                                                    className="border-2 border-gray-300 p-2 rounded-md focus:outline-none w-full"
                                                    placeholder="City"
                                                    value={business.city}
                                                    onChange={handleInputChange}
                                                    required
                                                />
                                            </div>
                                            <div className="flex flex-col w-1/2 pr-4">
                                                <label htmlFor="state">
                                                    State:
                                                </label>
                                                <input
                                                    id="state"
                                                    name="state"
                                                    type="text"
                                                    className="border-2 border-gray-300 p-2 rounded-md focus:outline-none w-full"
                                                    placeholder="State"
                                                    value={business.state}
                                                    onChange={handleInputChange}
                                                    required
                                                />
                                            </div>
                                        </div>
                                        <label htmlFor="categories">
                                            Categories:
                                        </label>
                                        <input
                                            id="categories"
                                            name="categories"
                                            type="text"
                                            className="mb-4 border-2 border-gray-300 p-2 rounded-md focus:outline-none mr-4"
                                            placeholder="Categories"
                                            value={business.categories}
                                            onChange={handleInputChange}
                                            required
                                        />
                                        <label htmlFor="image">Image:</label>
                                        <input
                                            id="image"
                                            name="image"
                                            type="file"
                                            accept="image/*"
                                            className="mb-4 border-2 border-gray-300 bg-white p-2 rounded-md focus:outline-none mr-4"
                                            onChange={(event) => {
                                                if (
                                                    event.target.files &&
                                                    event.target.files[0]
                                                ) {
                                                    setBusinessPic(
                                                        event.target.files[0]
                                                    );
                                                }
                                            }}
                                            required
                                        />
                                        <label htmlFor="description">
                                            Description:
                                        </label>
                                        <textarea
                                            id="description"
                                            name="description"
                                            className="h-60 border-2 border-gray-300 p-2 rounded-md focus:outline-none mr-4"
                                            placeholder="Description"
                                            value={business.description}
                                            onChange={handleInputChange}
                                            required
                                        />
                                    </div>
                                    <div className="flex flex-col my-4 w-1/2">
                                        <div className="flex flex-wrap justify-between">
                                            {Object.keys(business.hours).map(
                                                (day) => (
                                                    <div
                                                        key={day}
                                                        className="flex flex-col mb-4 w-1/3 pr-4">
                                                        <label
                                                            htmlFor={
                                                                day
                                                            }>{`${day} Hours:`}</label>
                                                        <input
                                                            id={day}
                                                            name={day}
                                                            type="text"
                                                            className="border-2 border-gray-300 p-2 rounded-md focus:outline-none"
                                                            placeholder="00:00-23:59"
                                                            value={
                                                                business.hours[
                                                                    day
                                                                ]
                                                            }
                                                            onChange={
                                                                handleHoursChange
                                                            }
                                                        />
                                                    </div>
                                                )
                                            )}
                                        </div>

                                        <label htmlFor="location">
                                            Location:
                                        </label>
                                        <div className="flex flex-row justify-start items-center">
                                            <p className="mr-5">
                                                Lat:{' '}
                                                <span className="font-bold">
                                                    {latitude}
                                                </span>
                                            </p>
                                            <p>
                                                Lng:{' '}
                                                <span className="font-bold">
                                                    {longitude}
                                                </span>
                                            </p>
                                        </div>

                                        <div className="pt-1 h-full">
                                            <MapComponent
                                                height="100%"
                                                width="400px"
                                                setLng={setLongitude}
                                                setLat={setLatitude}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="flex flex-row justify-end items-center">
                                    <button
                                        type="submit"
                                        className="btn bg-blue-500 hover:bg-blue-700 text-white rounded-md">
                                        Register
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

export default RegisterBusiness;
